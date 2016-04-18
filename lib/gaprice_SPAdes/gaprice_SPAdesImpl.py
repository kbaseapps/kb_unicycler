#BEGIN_HEADER
# The header block is where all import statments should live
from __future__ import print_function
import os
import re
import uuid
from pprint import pprint, pformat
from biokbase.workspace.client import Workspace as workspaceService
import requests
import json
import psutil
import subprocess
import hashlib
import numpy as np
#END_HEADER


class gaprice_SPAdes:
    '''
    Module Name:
    gaprice_SPAdes

    Module Description:
    A KBase module: gaprice_SPAdes
Simple wrapper for the SPAdes assembler.
http://bioinf.spbau.ru/spades

Currently only supports assembling one PairedEndLibrary at a time.
Always runs in careful mode.
Runs 3 threads / CPU.
Maximum memory use is set to available memory - 1G.
Autodetection is used for the PHRED quality offset and k-mer sizes.
A coverage cutoff is not specified.
Does not currently support assembling metagenomics reads.
    '''

    ######## WARNING FOR GEVENT USERS #######
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    #########################################
    #BEGIN_CLASS_HEADER
    # Class variables and functions can be defined in this block
    REPRESS_SPADES_OUTPUT = False # for testing. Should be false in production.
    
    PAIRED_END_TYPE = 'PairedEndLibrary'
    # one of these should be deprecated
    MODULE_NAMES = ['KBaseAssembly', 'KBaseFile'] 
    
    PARAM_IN_WS = 'workspace_name'
    PARAM_IN_LIB = 'read_library_name'
    PARAM_IN_CS_NAME = 'output_contigset_name'
    PARAM_IN_SINGLE_CELL = 'single_cell'
    VERSION = '0.0.1'
    
    THREADS_PER_CORE = 3
    MEMORY_OFFSET_GB = 1 # 1GB
    MIN_MEMORY_GB = 5
    GB = 1000000000
    
    URL_WS = 'workspace-url'
    URL_SHOCK = 'shock-url'
    
    def log(self, message):
        print(message);
    
    
    def shock_download(self, token, handle):
        self.log('Downloading from shock via handle:')
        self.log(pformat(handle))
        file_name = handle['id']
        if 'file_name' in handle:
            fr_file_name = handle['file_name']
        
        ### NOTE: this section is what could be replaced by the transform services
        file_path = os.path.join(self.scratch , fr_file_name)
        with open(file_path, 'w', 0) as fhandle:
            self.log('downloading reads file: ' + str(file_path))
            headers = {'Authorization': 'OAuth ' + token}
            node_url = handle['url'] + '/node/' + handle['id'] + '?download'
            r = requests.get(node_url, stream=True, headers=headers)
            if not r.ok:
                try:
                    err = json.loads(r.content)['error'][0]
                except:
                    self.log("Couldn't parse response error content: " +
                         r.content)
                    r.raise_for_status()
                raise Exception(str(err))
            for chunk in r.iter_content(1024):
                if not chunk: break
                fhandle.write(chunk)
        self.log('done')
        return file_path


    # Helper script borrowed from the transform service, logger removed
    def upload_file_to_shock(self, filePath, token):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """

        if token is None:
            raise Exception("Authentication token required!")

        #build the header
        header = dict()
        header["Authorization"] = "Oauth {0}".format(token)

        if filePath is None:
            raise Exception("No file given for upload to SHOCK!")
        
        with open(os.path.abspath(filePath), 'rb') as dataFile:
            response = requests.post(self.shockURL + '/node', headers = header,
                                     data=dataFile, allow_redirects=True)

        if not response.ok:
            response.raise_for_status()

        result = response.json()

        if result['error']:
            raise Exception(result['error'][0])
        else:
            return result["data"]


    def exec_spades(self, single_cell, for_file, rev_file):
        # construct the SPAdes command
        threads = psutil.cpu_count() * self.THREADS_PER_CORE
        mem = (psutil.virtual_memory().available / self.GB -
               self.MEMORY_OFFSET_GB)
        if mem < self.MIN_MEMORY_GB:
            raise ValueError(
                'Only ' + str(psutil.virtual_memory().available) +
                ' bytes of memory are available. The SPAdes wrapper will ' +
                ' not run without at least ' +
                str(self.MIN_MEMORY_GB + self.MEMORY_OFFSET_GB) +
                ' bytes available')
        outdir = os.path.join(self.scratch, 'spades_output_dir')
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        tmpdir = os.path.join(self.scratch, 'spades_tmp_dir')
        if not os.path.exists(tmpdir):
            os.makedirs(tmpdir)
        cmd = ['spades.py', '--careful', '--threads', str(threads),
               '--memory', str(mem), '-o', outdir, '--tmp-dir', tmpdir]
        if single_cell:
            cmd += ['--sc']
        if rev_file:
            cmd += ['--pe1-1', for_file, '--pe1-2', rev_file]
        else:
            cmd += ['--pe1-12', for_file]
        self.log('Running SPAdes command line:')
        self.log(cmd)
        stdout_file = os.path.join(self.scratch, 'spades_stdout')
        stderr_file = os.path.join(self.scratch, 'spades_stderr')
        
        with open(stdout_file, 'w') as spdout, open(stderr_file, 'w') as spderr:
            p = subprocess.Popen(cmd,
                    cwd = self.scratch,
#                     stdout = spdout, 
#                     stderr = spderr,
                    shell = False)
            retcode = p.wait()
        
#         self.log('Standard out:')
#         if self.REPRESS_SPADES_OUTPUT:
#             print('SPAdes output repressed but saved locally.')
#         else:
#             with open(stdout_file) as spdout:
#                 for line in spdout:
#                     self.log(line)
#         
#         self.log('Standard error:')
#         with open(stderr_file) as spderr:
#             for line in spderr:
#                 self.log(line)
        
        self.log('Return code: ' + str(retcode))
        if p.returncode != 0:
#             errsize = os.stat(stderr_file).st_size
#             if errsize > 50000:
#                 errmsg = 'Standard error too large to return'
#             else:
#                 with open(stderr_file) as spderr:
#                     errmsg = 'Standard error:\n' + spderr.read()
            raise ValueError('Error running SPAdes, return code: ' + 
                             str(retcode) + '\n') # + errmsg)
        
        return outdir


    # adapted from 
    # https://github.com/kbase/transform/blob/master/plugins/scripts/convert/trns_transform_KBaseFile_AssemblyFile_to_KBaseGenomes_ContigSet.py
    def convert_to_contigs(self, input_file_name, source, contigset_id,
                           shock_id):
        """
        Converts fasta to KBaseGenomes.ContigSet and saves to WS.
        Note the MD5 for the contig is generated by uppercasing the sequence.
        The ContigSet MD5 is generated by taking the MD5 of joining the sorted list
        of individual contig's MD5s with a comma separator
        Args:
            input_file_name: A file name for the input FASTA data.
            contigset_id: The id of the ContigSet. If not
                specified the name will default to the name of the input file
                appended with "_contig_set"'
            shock_id: Shock id for the fasta file if it already exists in shock
        """
    
        self.log('Starting conversion of FASTA to KBaseGenomes.ContigSet')
    
        self.log('Building Object.')
    
        if not os.path.isfile(input_file_name):
            raise Exception('The input file name {0} is not a file!'.format(
                input_file_name))
    
        # default if not too large
        contig_set_has_sequences = True
    
        fasta_filesize = os.stat(input_file_name).st_size
        if fasta_filesize > 900000000:
            # Fasta file too large to save sequences into the ContigSet object.
            self.log(
                'The FASTA input file is too large to fit in the workspace. ' +
                'A ContigSet object will be created without sequences, but ' +
                'will contain a reference to the file.')
            contig_set_has_sequences = False
    
        with open(input_file_name, 'r') as input_file_handle:
            fasta_header = None
            sequence_list = []
            fasta_dict = dict()
            first_header_found = False
            contig_set_md5_list = []
            # Pattern for replacing white space
            pattern = re.compile(r'\s+')
            for current_line in input_file_handle:
                if (current_line[0] == '>'):
                    # found a header line
                    # Wrap up previous fasta sequence
                    if (not sequence_list) and first_header_found:
                        raise Exception(
                            'There is no sequence related to FASTA record: {0}'
                            .format(fasta_header))
                    if not first_header_found:
                        first_header_found = True
                    else:
                        # build up sequence and remove all white space
                        total_sequence = ''.join(sequence_list)
                        total_sequence = re.sub(pattern, '', total_sequence)
                        if not total_sequence:
                            raise Exception(
                                'There is no sequence related to FASTA record: '
                                + fasta_header)
                        try:
                            fasta_key, fasta_description = \
                                fasta_header.strip().split(' ', 1)
                        except:
                            fasta_key = fasta_header.strip()
                            fasta_description = None
                        contig_dict = dict()
                        contig_dict['id'] = fasta_key
                        contig_dict['length'] = len(total_sequence)
                        contig_dict['name'] = fasta_key
                        md5wrds = 'Note MD5 is generated from uppercasing ' + \
                            'the sequence'
                        if fasta_description:
                            fasta_description += '. ' + md5wrds
                        else:
                            fasta_description = md5wrds
                        contig_dict['description'] = fasta_description
                        contig_md5 = hashlib.md5(
                            total_sequence.upper()).hexdigest()
                        contig_dict['md5'] = contig_md5
                        contig_set_md5_list.append(contig_md5)
                        if contig_set_has_sequences:
                            contig_dict['sequence'] = total_sequence
                        else:
                            contig_dict['sequence'] = None
                        fasta_dict[fasta_header] = contig_dict
        
                        # get set up for next fasta sequence
                        sequence_list = []
                    fasta_header = current_line.replace('>', '').strip()
                else:
                    sequence_list.append(current_line)
        
        # wrap up last fasta sequence, should really make this a method
        if (not sequence_list) and first_header_found:
            raise Exception(
                "There is no sequence related to FASTA record: {0}".format(
                    fasta_header))
        elif not first_header_found:
            raise Exception("There are no contigs in this file")
        else:
            # build up sequence and remove all white space
            total_sequence = ''.join(sequence_list)
            total_sequence = re.sub(pattern, '', total_sequence)
            if not total_sequence:
                raise Exception(
                    "There is no sequence related to FASTA record: " +
                    fasta_header)
            try:
                fasta_key, fasta_description = \
                    fasta_header.strip().split(' ', 1)
            except:
                fasta_key = fasta_header.strip()
                fasta_description = None
            contig_dict = dict()
            contig_dict['id'] = fasta_key
            contig_dict['length'] = len(total_sequence)
            contig_dict['name'] = fasta_key
            md5wrds = 'Note MD5 is generated from uppercasing ' + \
                'the sequence'
            if fasta_description:
                fasta_description += '. ' + md5wrds
            else:
                fasta_description = md5wrds
            contig_dict['description'] = fasta_description
            contig_md5 = hashlib.md5(total_sequence.upper()).hexdigest()
            contig_dict['md5'] = contig_md5
            contig_set_md5_list.append(contig_md5)
            if contig_set_has_sequences:
                contig_dict['sequence'] = total_sequence
            else:
                contig_dict['sequence'] = None
            fasta_dict[fasta_header] = contig_dict
    
        contig_set_dict = dict()
        contig_set_dict['md5'] = hashlib.md5(','.join(sorted(
            contig_set_md5_list))).hexdigest()
        contig_set_dict['id'] = contigset_id
        contig_set_dict['name'] = contigset_id
        s = 'unknown'
        if source and source['source']:
            s = source['source']
        contig_set_dict['source'] = s
        sid = os.path.basename(input_file_name)
        if source and source['source_id']:
            sid = source['source_id']
        contig_set_dict['source_id'] = sid
        contig_set_dict['contigs'] = [fasta_dict[x] for x in sorted(
            fasta_dict.keys())]
    
        contig_set_dict['fasta_ref'] = shock_id
    
        self.log('Conversion completed.')
        return contig_set_dict


    def load_report(self, contigset,cs_ref, params, wscli, wsid, provenance):
        lengths = [contig['length'] for contig in contigset['contigs']]
        
        report = ''
        report += 'ContigSet saved to: ' + params[self.PARAM_IN_WS] + '/' + \
            params[self.PARAM_IN_CS_NAME]+'\n'
        report += 'Assembled into ' + str(len(lengths)) + ' contigs.\n'
        report += 'Avg Length: ' + str(sum(lengths) / float(len(lengths))) + \
            ' bp.\n'

        # compute a simple contig length distribution
        bins = 10
        counts, edges = np.histogram(lengths, bins)
        report += 'Contig Length Distribution (# of contigs -- min to max ' +\
            'basepairs):\n'
        for c in range(bins):
            report += '   ' + str(counts[c]) + '\t--\t' + str(edges[c]) +\
                ' to ' + str(edges[c + 1]) + ' bp\n'

        reportObj = {
            'objects_created':[{'ref': cs_ref,
                                'description':'Assembled contigs'}],
            'text_message':report
        }

        reportName = 'SPAdes_report_'+str(hex(uuid.getnode()))
        report_obj_info = wscli.save_objects({
                'id': wsid,
                'objects':[
                    {
                        'type':'KBaseReport.Report',
                        'data':reportObj,
                        'name':reportName,
                        'meta':{},
                        'hidden':1,
                        'provenance':provenance
                    }
                ]
            })[0]
        reportRef = self.make_ref(report_obj_info)
        return reportName, reportRef


    def make_ref(cls, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.workspaceURL = config[self.URL_WS]
        self.shockURL = config[self.URL_SHOCK]
        self.scratch = os.path.abspath(config['scratch'])
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)
        #END_CONSTRUCTOR
        pass

    def run_SPAdes(self, ctx, params):
        # ctx is the context object
        # return variables are: output
        #BEGIN run_SPAdes
        
        # A whole lot of this is adapted or outright copied from
        # https://github.com/msneddon/MEGAHIT
        self.log('Running run_SPAdes with params:')
        self.log(pformat(params))
        
        token = ctx['token']

        # TODO check contents of types - e.g. metagenomics, outside reads, check gzip etc.

        #### do some basic checks
        objref = ''
        if self.PARAM_IN_WS not in params:
            raise ValueError(self.PARAM_IN_WS + ' parameter is required')
        if self.PARAM_IN_LIB not in params:
            raise ValueError(self.PARAM_IN_LIB + ' parameter is required')
        if self.PARAM_IN_CS_NAME not in params:
            raise ValueError(self.PARAM_IN_CS_NAME + ' parameter is required')
        single_cell = (self.PARAM_IN_SINGLE_CELL in params and
            params[self.PARAM_IN_SINGLE_CELL] == 0)

        #### Get the read library
        ws = workspaceService(self.workspaceURL, token=token)
        reads = ws.get_objects([{'ref': params[self.PARAM_IN_WS] + '/' +
                                   params[self.PARAM_IN_LIB]}])[0]
        data = reads['data']
        info = reads['info']
        # Object Info Contents
        # 0 - obj_id objid
        # 1 - obj_name name
        # 2 - type_string type
        # 3 - timestamp save_date
        # 4 - int version
        # 5 - username saved_by
        # 6 - ws_id wsid
        # 7 - ws_name workspace
        # 8 - string chsum
        # 9 - int size 
        # 10 - usermeta meta
        
        # Might need to do version checking here.
        module_name, type_name = info[2].split('-')[0].split('.')
        in_lib_ref = self.make_ref(info)
        source = None
        if 'source' in data:
            source = data['source']

        if (module_name not in self.MODULE_NAMES or
            type_name != self.PAIRED_END_TYPE):
            raise ValueError(
                'Only the types ' +
                self.MODULE_NAMES[0] + '.' + self.PAIRED_END_TYPE +
                ' and ' + self.MODULE_NAMES[1] + '.' + self.PAIRED_END_TYPE +
                ' are supported')

        # TODO make this a method and and more checking
        # lib1 = KBaseFile, handle_1 = KBaseAssembly
        if 'lib1' in data:
            forward_reads = data['lib1']['file']
        elif 'handle_1' in data:
            forward_reads = data['handle_1']
        if 'lib2' in data:
            reverse_reads = data['lib2']['file']
        elif 'handle_2' in data:
            reverse_reads = data['handle_2']
        else:
            reverse_reads=False
        
        for_file = self.shock_download(token, forward_reads)
        rev_file = None
        if (reverse_reads):
            rev_file = self.shock_download(token, reverse_reads)
            
        
        spades_out = self.exec_spades(single_cell, for_file, rev_file)
        self.log('SPAdes output dir: ' + spades_out)
        
        # parse the output and save back to KBase
        output_contigs = os.path.join(spades_out, 'scaffolds.fasta')
        
        shockid = self.upload_file_to_shock(output_contigs, token)['id']
            
        cs = self.convert_to_contigs(output_contigs, source,
                                     params[self.PARAM_IN_CS_NAME], shockid)
        
        # load the method provenance from the context object
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        # add additional info to provenance here, in this case the input data object reference
        provenance[0]['input_ws_objects']=[in_lib_ref]

        # save the contigset output
        new_obj_info = ws.save_objects({
                'id':info[6], # set the output workspace ID
                'objects':[
                    {
                        'type':'KBaseGenomes.ContigSet',
                        'data':cs,
                        'name':params[self.PARAM_IN_CS_NAME],
                        'meta':{},
                        'provenance':provenance
                    }
                ]
            })[0]
        cs_ref = self.make_ref(new_obj_info)
       
        report_name, report_ref = self.load_report(
            cs, cs_ref, params, ws, info[6], provenance)

        output = {'report_name': report_name,
                  'report_ref': report_ref
                  }
        #END run_SPAdes

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_SPAdes return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
