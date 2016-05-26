#BEGIN_HEADER
# The header block is where all import statements should live
from __future__ import print_function
import os
import re
import uuid
from pprint import pformat
from biokbase.workspace.client import Workspace as workspaceService  # @UnresolvedImport @IgnorePep8
import requests
import json
import psutil
import subprocess
import hashlib
import numpy as np
import yaml
from gaprice_SPAdes_test.GenericClient import GenericClient, ServerError
# from gaprice_SPAdes_test.kbdynclient import KBDynClient, ServerError
import time


class ShockException(Exception):
    pass

#END_HEADER


class gaprice_SPAdes_test:
    '''
    Module Name:
    gaprice_SPAdes_test

    Module Description:
    A KBase module: gaprice_SPAdes
Simple wrapper for the SPAdes assembler.
http://bioinf.spbau.ru/spades

Always runs in careful mode.
Runs 3 threads / CPU.
Maximum memory use is set to available memory - 1G.
Autodetection is used for the PHRED quality offset and k-mer sizes.
A coverage cutoff is not specified.
    '''

    ######## WARNING FOR GEVENT USERS #######
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    #########################################
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/mrcreosote/gaprice_SPAdes"
    GIT_COMMIT_HASH = "41086fbc4658be1b14e2e623addbcf8e8ac5fff6"
    
    #BEGIN_CLASS_HEADER
    # Class variables and functions can be defined in this block
    DISABLE_SPADES_OUTPUT = False  # should be False in production

    PARAM_IN_WS = 'workspace_name'
    PARAM_IN_LIB = 'read_libraries'
    PARAM_IN_CS_NAME = 'output_contigset_name'
    PARAM_IN_DNA_SOURCE = 'dna_source'
    PARAM_IN_SINGLE_CELL = 'single_cell'
    PARAM_IN_METAGENOME = 'metagenome'

    INVALID_WS_OBJ_NAME_RE = re.compile('[^\\w\\|._-]')
    INVALID_WS_NAME_RE = re.compile('[^\\w:._-]')

    THREADS_PER_CORE = 3
    MEMORY_OFFSET_GB = 1  # 1GB
    MIN_MEMORY_GB = 5
    GB = 1000000000

    URL_WS = 'workspace-url'
    URL_SHOCK = 'shock-url'
    URL_KB_END = 'kbase-endpoint'

    TRUE = 'true'
    FALSE = 'false'

    def log(self, message, prefix_newline=False):
        print(('\n' if prefix_newline else '') +
              str(time.time()) + ': ' + str(message))

    def check_shock_response(self, response, errtxt):
        if not response.ok:
            try:
                err = json.loads(response.content)['error'][0]
            except:
                # this means shock is down or not responding.
                self.log("Couldn't parse response error content from Shock: " +
                         response.content)
                response.raise_for_status()
            raise ShockException(errtxt + str(err))

    # Helper script borrowed from the transform service, logger removed
    def upload_file_to_shock(self, file_path, token):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """

        if token is None:
            raise Exception("Authentication token required!")

        header = {'Authorization': "Oauth {0}".format(token)}

        if file_path is None:
            raise Exception("No file given for upload to SHOCK!")

        with open(os.path.abspath(file_path), 'rb') as data_file:
            files = {'upload': data_file}
            response = requests.post(
                self.shockURL + '/node', headers=header, files=files,
                stream=True, allow_redirects=True)
        self.check_shock_response(
            response, ('Error trying to upload contig FASTA file {} to Shock: '
                       ).format(file_path))
        return response.json()['data']

    def generate_spades_yaml(self, reads_data):
        left = []  # fwd in fr orientation
        right = []  # rev
        interlaced = []
        for read in reads_data:
            if 'rev_file' in read and read['rev_file']:
                left.append(read['fwd_file'])
                right.append(read['rev_file'])
            else:
                interlaced.append(read['fwd_file'])
        yml = [{'type': 'paired-end',
                'orientation': 'fr'}]
        if left:
            yml[0]['left reads'] = left
            yml[0]['right reads'] = right
        if interlaced:
            yml[0]['interlaced reads'] = interlaced
        yml_path = os.path.join(self.scratch, 'run.yaml')
        with open(yml_path, 'w') as yml_file:
            yaml.safe_dump(yml, yml_file)
        return yml_path

    def exec_spades(self, dna_source, reads_data):
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

        cmd = ['spades.py', '--threads', str(threads),
               '--memory', str(mem), '-o', outdir, '--tmp-dir', tmpdir]
        if dna_source == self.PARAM_IN_SINGLE_CELL:
            cmd += ['--sc']
        if dna_source == self.PARAM_IN_METAGENOME:
            cmd += ['--meta']
        else:
            cmd += ['--careful']
        cmd += ['--dataset', self.generate_spades_yaml(reads_data)]
        self.log('Running SPAdes command line:')
        self.log(cmd)

        if self.DISABLE_SPADES_OUTPUT:
            with open(os.devnull, 'w') as null:
                p = subprocess.Popen(cmd, cwd=self.scratch, shell=False,
                                     stdout=null)
        else:
            p = subprocess.Popen(cmd, cwd=self.scratch, shell=False)
        retcode = p.wait()

        self.log('Return code: ' + str(retcode))
        if p.returncode != 0:
            raise ValueError('Error running SPAdes, return code: ' +
                             str(retcode) + '\n')

        return outdir

    # adapted from
    # https://github.com/kbase/transform/blob/master/plugins/scripts/convert/trns_transform_KBaseFile_AssemblyFile_to_KBaseGenomes_ContigSet.py
    # which was adapted from an early version of
    # https://github.com/kbase/transform/blob/master/plugins/scripts/upload/trns_transform_FASTA_DNA_Assembly_to_KBaseGenomes_ContigSet.py
    def convert_to_contigs(self, input_file_name, source, contigset_id,
                           shock_id):
        """
        Converts fasta to KBaseGenomes.ContigSet and saves to WS.
        Note the MD5 for the contig is generated by uppercasing the sequence.
        The ContigSet MD5 is generated by taking the MD5 of joining the sorted
        list of individual contig's MD5s with a comma separator
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
                                'There is no sequence related to FASTA ' +
                                'record: ' + fasta_header)
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
        # joining by commas is goofy, but keep consistency with the uploader
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

    def load_report(self, contigset, cs_ref, params, wscli, wsid, provenance):
        lengths = [contig['length'] for contig in contigset['contigs']]

        report = ''
        report += 'ContigSet saved to: ' + params[self.PARAM_IN_WS] + '/' + \
            params[self.PARAM_IN_CS_NAME]+'\n'
        report += 'Assembled into ' + str(len(lengths)) + ' contigs.\n'
        report += 'Avg Length: ' + str(sum(lengths) / float(len(lengths))) + \
            ' bp.\n'

        # compute a simple contig length distribution
        bins = 10
        counts, edges = np.histogram(lengths, bins)  # @UndefinedVariable
        report += 'Contig Length Distribution (# of contigs -- min to max ' +\
            'basepairs):\n'
        for c in range(bins):
            report += '   ' + str(counts[c]) + '\t--\t' + str(edges[c]) +\
                ' to ' + str(edges[c + 1]) + ' bp\n'

        reportObj = {
            'objects_created': [{'ref': cs_ref,
                                 'description': 'Assembled contigs'}],
            'text_message': report
        }

        reportName = 'SPAdes_report_' + str(uuid.uuid4())
        report_obj_info = wscli.save_objects({
                'id': wsid,
                'objects': [
                    {
                        'type': 'KBaseReport.Report',
                        'data': reportObj,
                        'name': reportName,
                        'hidden': 1,
                        'provenance': provenance
                    }
                ]
            })[0]
        reportRef = self.make_ref(report_obj_info)
        return reportName, reportRef

    def make_ref(self, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])

    def check_reads(self, params, reads):

        for obj_name in reads:
            rds = reads[obj_name]
            obj_ref = rds['ref']
            if rds['read_orientation_outward'] == self.TRUE:
                raise ValueError(
                    ('Reads object {} ({}) is marked as having outward ' +
                     'oriented reads, which SPAdes does not ' +
                     'support.').format(obj_name, obj_ref))

            # ideally types would be firm enough that we could rely on the
            # metagenomic boolean. However KBaseAssembly doesn't have the field
            # and it's optional anyway. Ideally fix those issues and then set
            # the --meta command line flag automatically based on the type
            if (rds['single_genome'] == self.TRUE and
                    params[self.PARAM_IN_DNA_SOURCE] ==
                    self.PARAM_IN_METAGENOME):
                raise ValueError(
                    ('Reads object {} ({}) is marked as containing dna from ' +
                     'a single genome but the assembly method was specified ' +
                     'as metagenomic').format(obj_name, obj_ref))
            if (rds['single_genome'] == self.FALSE and
                    params[self.PARAM_IN_DNA_SOURCE] !=
                    self.PARAM_IN_METAGENOME):
                raise ValueError(
                    ('Reads object {} ({}) is marked as containing ' +
                     'metagenomic data but the assembly method was not ' +
                     'specified as metagenomic').format(obj_name, obj_ref))

    def process_params(self, params):
        if (self.PARAM_IN_WS not in params or
                not params[self.PARAM_IN_WS]):
            raise ValueError(self.PARAM_IN_WS + ' parameter is required')
        if self.INVALID_WS_NAME_RE.search(params[self.PARAM_IN_WS]):
            raise ValueError('Invalid workspace name ' +
                             params[self.PARAM_IN_WS])
        if self.PARAM_IN_LIB not in params:
            raise ValueError(self.PARAM_IN_LIB + ' parameter is required')
        if type(params[self.PARAM_IN_LIB]) != list:
            raise ValueError(self.PARAM_IN_LIB + ' must be a list')
        if not params[self.PARAM_IN_LIB]:
            raise ValueError('At least one reads library must be provided')
        for l in params[self.PARAM_IN_LIB]:
            if self.INVALID_WS_OBJ_NAME_RE.search(l):
                raise ValueError('Invalid workspace object name ' + l)
        if (self.PARAM_IN_CS_NAME not in params or
                not params[self.PARAM_IN_CS_NAME]):
            raise ValueError(self.PARAM_IN_CS_NAME + ' parameter is required')
        if self.INVALID_WS_OBJ_NAME_RE.search(params[self.PARAM_IN_CS_NAME]):
            raise ValueError('Invalid workspace object name ' +
                             params[self.PARAM_IN_CS_NAME])
        if self.PARAM_IN_DNA_SOURCE in params:
            s = params[self.PARAM_IN_DNA_SOURCE]
            if s not in [self.PARAM_IN_SINGLE_CELL, self.PARAM_IN_METAGENOME]:
                params[self.PARAM_IN_DNA_SOURCE] = None
        else:
            params[self.PARAM_IN_DNA_SOURCE] = None

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.generic_clientURL = os.environ['SDK_CALLBACK_URL']
        self.log('Callback URL: ' + self.generic_clientURL)
        self.workspaceURL = config[self.URL_WS]
        self.shockURL = config[self.URL_SHOCK]
        self.catalogURL = config[self.URL_KB_END] + '/catalog'
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
        self.log('Running run_SPAdes with params:\n' + pformat(params))

        token = ctx['token']

        self.process_params(params)

        # Get the reads library
#         kbase = KBDynClient(self.catalogURL, ctx)
#         kbase.load_module('kb_read_library_to_file', version='dev')
        reads_params = {self.PARAM_IN_WS: params[self.PARAM_IN_WS],
                        self.PARAM_IN_LIB: params[self.PARAM_IN_LIB]}

        gc = GenericClient(self.generic_clientURL, use_url_lookup=False,
                           token=token)

        typeerr = ('Supported types: KBaseFile.SingleEndLibrary ' +
                   'KBaseFile.PairedEndLibrary ' +
                   'KBaseAssembly.SingleEndLibrary ' +
                   'KBaseAssembly.PairedEndLibrary')
        try:
            # reads = kbase.mods.kb_read_library_to_file \
            #     .convert_read_library_to_file(reads_params)['files']
            reads = gc.asynchronous_call(
                "kb_read_library_to_file.convert_read_library_to_file",
                [reads_params], json_rpc_context={"service_ver": "dev"}
                )[0]['files']
        except ServerError as se:
            self.log('logging stacktrace from dynamic client error')
            self.log(se.data)
            if typeerr in se.message:
                prefix = se.message.split('.')[0]
                raise ValueError(
                    prefix + '. Only the types ' +
                    'KBaseAssembly.PairedEndLibrary ' +
                    'and KBaseFile.PairedEndLibrary are supported')
            else:
                raise

        self.log('Got reads data from converter:\n' + pformat(reads))

        self.check_reads(params, reads)

        reads_data = []
        for r in reads:
            f = reads[r]['files']
            if 'sing' in f:
                raise ValueError(('{} is a single end read library, which ' +
                                  'is not currently supported.').format(r))
            if 'inter' in f:
                reads_data.append({'fwd_file': f['inter']})
            elif 'fwd' in f:
                reads_data.append({'fwd_file': f['fwd'], 'rev_file': f['rev']})
            else:
                raise ValueError('Something is very wrong with read lib' + r)

        spades_out = self.exec_spades(params[self.PARAM_IN_DNA_SOURCE],
                                      reads_data)
        self.log('SPAdes output dir: ' + spades_out)

        # parse the output and save back to KBase
        source = {'source': 'See provenance',
                  'source_id': 'See provenance'}
        output_contigs = os.path.join(spades_out, 'scaffolds.fasta')

        self.log('Uploading FASTA file to Shock')
        shockid = self.upload_file_to_shock(output_contigs, token)['id']

        cs = self.convert_to_contigs(output_contigs, source,
                                     params[self.PARAM_IN_CS_NAME], shockid)

        # load the method provenance
#         gc = GenericClient(self.generic_clientURL, use_url_lookup=False,
#                            token=token)
#         provenance = gc.sync_call("CallbackServer.get_provenance", [])[0]
#         provenance = [{}]
#         if 'provenance' in ctx:
#             provenance = ctx['provenance']
        provenance = ctx.provenance()
        # add additional info to provenance here, in this case the input data
        # object reference
        iwso = 'input_ws_objects'
        if not provenance[0].get(iwso):
            # only mess with the provenance if the auto-provenance doesn't
            # add wsids yet, also can be used for testing
            provenance[0][iwso] = \
                [reads[x]['ref'] for x in reads]

        ws_id = reads[r]['ref'].split('/')[0]
        ws = workspaceService(self.workspaceURL, token=token)

        # save the contigset output
        new_obj_info = ws.save_objects({
                'id': ws_id,
                'objects': [
                    {
                        'type': 'KBaseGenomes.ContigSet',
                        'data': cs,
                        'name': params[self.PARAM_IN_CS_NAME],
                        'provenance': provenance
                    }
                ]
            })[0]
        cs_ref = self.make_ref(new_obj_info)

        report_name, report_ref = self.load_report(
            cs, cs_ref, params, ws, ws_id, provenance)

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

    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        del ctx  # shut up pep8
        #END_STATUS
        return [returnVal]
