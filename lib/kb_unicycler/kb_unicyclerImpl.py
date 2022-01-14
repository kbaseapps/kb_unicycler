# -*- coding: utf-8 -*-
#BEGIN_HEADER
from __future__ import print_function
import os
import re
import uuid
import requests
import json
import psutil
import subprocess
import numpy as np
import yaml
import time
import zipfile
from pprint import pformat
import sys
from html import escape
from shutil import copy, copytree, move

from installed_clients.WorkspaceClient import Workspace
from installed_clients.ReadsUtilsClient import ReadsUtils  # @IgnorePep8
from installed_clients.baseclient import ServerError
from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.kb_quastClient import kb_quast
from SetAPI.SetAPIServiceClient import SetAPI
#END_HEADER


class kb_unicycler:
    '''
    Module Name:
    kb_unicycler

    Module Description:
    A KBase module: kb_unicycler
A wrapper for the unicycler assembler
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "1.0.0"
    GIT_URL = "git@github.com:jmchandonia/kb_unicycler.git"
    GIT_COMMIT_HASH = "4fcf8960ce76ed3efa4bb75ddf689a0c78ca06d9"

    #BEGIN_CLASS_HEADER
    def log(self, target, message):
        if target is not None:
            target.append(message)
        print(message)
        sys.stdout.flush()

    # from kb_SPAdes/utils/spades_utils.py:
    def load_stats(self, console, input_file_name):
        self.log(console, 'Starting conversion of FASTA to KBaseGenomeAnnotations.Assembly')
        self.log(console, 'Building Object.')
        if not os.path.isfile(input_file_name):
            raise Exception('The input file name {0} is not a file!'.format(input_file_name))
        with open(input_file_name, 'r') as input_file_handle:
            contig_id = None
            sequence_len = 0
            length_dict = dict()
            coverage_dict = dict()
            circ_dict = dict()
            first_header_found = False
            # Pattern for replacing white space
            pattern = re.compile(r'\s+')
            for current_line in input_file_handle:
                if (current_line[0] == '>'):
                    # found a header line
                    # Wrap up previous fasta sequence
                    if not first_header_found:
                        first_header_found = True
                    else:
                        length_dict[contig_id] = sequence_len
                        sequence_len = 0
                    fasta_header = current_line.replace('>', '').strip()
                    # self.log(console, 'fasta header = '+fasta_header)
                    try:
                        fields = fasta_header.strip().split(' ')
                        contig_id = fields[0]
                        # don't trust length from header, we look at seqence:
                        # sequence_len = int(fields[1][7:]) if (fields[1].startswith('length=')) else 0
                        coverage = float(
                            fields[2][6:-1]) if (fields[2].startswith('depth=')) else 0.0
                        circ = 'Y' if ((len(fields) > 3) and (
                            'circular=true' in fields[3])) else 'N'
                        # length_dict[contig_id] = sequence_len
                        coverage_dict[contig_id] = coverage
                        circ_dict[contig_id] = circ
                    except (IndexError, ValueError, KeyError):
                        contig_id = fasta_header.strip()
                        coverage_dict[contig_id] = 0
                        circ_dict[contig_id] = 'N'
                else:
                    sequence_len += len(re.sub(pattern, '', current_line))
        # wrap up last fasta sequence
        if not first_header_found:
            raise Exception("There are no contigs in this file")
        else:
            length_dict[contig_id] = sequence_len
        return [length_dict, coverage_dict, circ_dict]

    # from kb_SPAdes/utils/spades_utils.py:
    def mkdir_p(self, path):
        """
        mkdir_p: make directory for given path
        """
        if not path:
            return
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def read_template(self, template_name):
        '''
        read in a template file and escape all html content
        used to display template contents
        '''
        with open(os.path.join(self.appdir, 'templates', template_name)) as file:
            lines = file.read()

        # escape all the html, display the results
        escaped_lines = escape(lines, quote=True)
        return escaped_lines

    def read_html(self, html_file):
        '''
        read in a html file
        '''
        with open(html_file) as file:
            lines = file.read()
        return lines

    # from kb_SPAdes/utils/spades_utils.py:
    def zip_folder(self, folder_path, output_path):
        """
        zip_folder: Zip the contents of an entire folder (with that folder included
        in the archive). Empty subfolders could be included in the archive as well
        if the commented portion is used.
        """
        with zipfile.ZipFile(output_path, 'w',
                             zipfile.ZIP_DEFLATED,
                             allowZip64=True) as ziph:
            for root, folders, files in os.walk(folder_path):
                for f in files:
                    absolute_path = os.path.join(root, f)
                    relative_path = os.path.join(os.path.basename(root), f)
                    # print "Adding {} to archive.".format(absolute_path)
                    ziph.write(absolute_path, relative_path)

        print("{} created successfully.".format(output_path))

    # from kb_SPAdes/utils/spades_utils.py:
    def generate_output_file_list(self, console, out_dir):
        """
        _generate_output_file_list: zip result files and generate file_links for report
        """
        self.log(console, 'start packing result files')

        output_files = list()

        output_directory = os.path.join(self.scratch, str(uuid.uuid4()))
        self.mkdir_p(output_directory)
        unicycler_output = os.path.join(output_directory, 'unicycler_output.zip')
        self.zip_folder(out_dir, unicycler_output)

        output_files.append({'path': unicycler_output,
                             'name': os.path.basename(unicycler_output),
                             'label': os.path.basename(unicycler_output),
                             'description': 'Output file(s) generated by Unicycler'})

        return output_files

    # adapted from kb_SPAdes/utils/spades_utils.py;
    # add templated report

    def generate_report(self, console, warnings, fa_file_name, params, out_dir, wsname):
        """
        Generating and saving report
        """
        self.log(console, 'Generating and saving report')

        fa_file_with_path = os.path.join(out_dir, fa_file_name)
        [length_stats, coverage_stats, circ_stats] = self.load_stats(console, fa_file_with_path)
        lengths = [length_stats[contig_id] for contig_id in length_stats]

        assembly_ref = wsname + '/' + params['output_contigset_name']

        report_text = ''
        report_text += 'Unicycler results saved to: ' + wsname + '/' + out_dir + '\n'
        report_text += 'Assembly saved to: ' + assembly_ref + '\n'
        report_text += 'Assembled into ' + str(len(lengths)) + ' contigs.\n'
        report_text += 'Avg Length: ' + str(sum(lengths) / float(len(lengths))) + ' bp.\n'

        # compute a simple contig length distribution
        bins = 10
        counts, edges = np.histogram(lengths, bins)
        report_text += 'Contig Length Distribution (# of contigs -- min to max ' + 'basepairs):\n'
        for c in range(bins):
            report_text += ('   ' + str(counts[c]) + '\t--\t' + str(edges[c]) + ' to ' +
                            str(edges[c + 1]) + ' bp\n')
        self.log(console, 'Running QUAST')
        kbq = kb_quast(self.callbackURL)
        quastret = kbq.run_QUAST(
            {'files': [{'path': fa_file_with_path, 'label': params['output_contigset_name']}]})
        # self.log(console,'quastret = '+pformat(quastret))

        # delete assembly file to keep it out of zip
        os.remove(fa_file_with_path)

        # check starting genes
        in_start = False
        ic = iter(console)
        for line in ic:
            if line.startswith('Rotating completed replicons'):
                while not line.startswith('Assembly complete'):
                    line = next(ic)
                    # self.log(console,'debug line = '+line)
                    fields = line.strip().split()
                    if len(fields) > 3 and fields[0] in circ_stats and circ_stats[fields[0]] == 'Y':
                        if fields[3] == 'none':
                            fields[3] = 'none found'
                        circ_stats[fields[0]] = 'Y, '+fields[3]

        # check circularization and make data table for report
        contig_data = []
        for contig_id in length_stats:
            contig_data.append({'contig_id': contig_id,
                                'circular': circ_stats[contig_id],
                                'coverage': coverage_stats[contig_id],
                                'length': length_stats[contig_id]})

        # self.log(console, 'contig_data = '+pformat(contig_data))

        # move quast output into main out_dir
        move(os.path.join(quastret['quast_path'], 'report.html'),
             os.path.join(out_dir, 'quast_report.html'))

        output_files = self.generate_output_file_list(console, out_dir)

        # render template
        template_file = 'unicycler_tabs.tt'
        tmpl_data = {
            'page_title': 'Unicycler Report',
            'data_array': contig_data,
            'cols': [
                {'data': 'contig_id',  'title': 'Contig ID'},
                {'data': 'circular',   'title': 'Circular, Starting Gene'},
                {'data': 'coverage',   'title': 'Coverage (x)'},
                {'data': 'length',   'title': 'Length (bp)'}
            ]
        }
        # tmpl_data['quast_output'] = '<iframe>'+self.read_html(os.path.join(quastret['quast_path'],'report.html'))+'</iframe>'
        # tmpl_data['quast_output'] = '<iframe frameborder="0" width="100%" height="100%" src="'+os.path.join(quastret['quast_path'],'report.html')+'"></iframe>'
        tmpl_data['quast_output'] = '<iframe style="display:block; width:100%; height:100vh; border:none;" src="quast_report.html"></iframe>'
        tmpl_data['tmpl_vars'] = json.dumps(tmpl_data, sort_keys=True, indent=2)
        tmpl_data['template_content'] = self.read_template(template_file)
        tmpl_data['unicycler_log'] = '<p><pre>'+'<br>'.join(filter(lambda line: not (
            line.startswith('tput') or line.lstrip().startswith('0 / ')), console))+'</pre></p>'

        # save report
        self.log(console, 'Saving report')
        report_file = 'unicycler_report.html'

        # copy the templates into 'scratch', where they can be accessed by KBaseReport
        try:
            copytree(
                os.path.join(self.appdir, 'templates'),
                os.path.join(self.scratch, 'templates')
            )
        except Exception as e:
            self.log(console, 'Exception copying tree. '+str(e))

        reportClient = KBaseReport(self.callbackURL)
        template_output = reportClient.render_template({
            'template_file': os.path.join(self.scratch, 'templates', template_file),
            'template_data_json': json.dumps(tmpl_data),
            'output_file': os.path.join(out_dir, report_file)
        })

        report_output = reportClient.create_extended_report(
            {'message': report_text,
             'objects_created': [{'ref': assembly_ref, 'description': 'Assembled contigs'}],
             'direct_html_link_index': 0,
             'file_links': output_files,
             'html_links': [{'path': out_dir,
                             'name': report_file,
                             'label': 'Unicycler report',
                             'description': 'description of template report'
                             }
                            ],
             'warnings': warnings,
             'report_object_name': 'kb_unicycler_report_' + str(uuid.uuid4()),
             'workspace_name': params['workspace_name']})

        return report_output['name'], report_output['ref']

    # get short paired reads, and combine into forward and reverse files

    def download_short_paired(self, console, token, wsname, short_paired_libraries):
        try:
            ruClient = ReadsUtils(url=self.callbackURL, token=token)

            # first, unpack any ReadsSets into the actual PairedEndLibrary referencs
            reads_refs = []
            # object info
            try:
                wsClient = Workspace(self.workspaceURL, token=token)
            except Exception as e:
                raise ValueError("unable to instantiate wsClient. "+str(e))

            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I,
                WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)  # object_info tuple
            for lib in short_paired_libraries:
                try:
                    obj_id = {'ref': lib if '/' in lib else (wsname + '/' + lib)}
                    lib_obj_info = wsClient.get_object_info_new({'objects': [obj_id]})[0]
                    lib_obj_type = lib_obj_info[TYPE_I]
                    # remove trailing version
                    lib_obj_type = re.sub('-[0-9]+\.[0-9]+$', "", lib_obj_type)
                    lib_ref = str(lib_obj_info[WSID_I])+'/' + \
                        str(lib_obj_info[OBJID_I])+'/'+str(lib_obj_info[VERSION_I])
                    if lib_obj_type == 'KBaseSets.ReadsSet':
                        # unpack it
                        try:
                            setAPIClient = SetAPI(url=self.serviceWizardURL, token=token)
                            self.log(console, 'getting reads set '+lib_ref)
                            readsSet = setAPIClient.get_reads_set_v1(
                                {'ref': lib_ref, 'include_item_info': 1})
                        except Exception as e:
                            raise ValueError(
                                'SetAPI FAILURE: Unable to get read library set object: (' + lib_ref + ')\n' + str(e))
                        for readsLibrary in readsSet['data']['items']:
                            reads_refs.append(readsLibrary['ref'])
                    else:
                        # use other reads objects "as is"
                        reads_refs.append(lib_ref)
                except Exception as e:
                    raise ValueError(
                        'Unable to get read library object: (' + str(lib) + ')' + str(e))

            # download all reads refs in one call, in separate files
            self.log(console, "Getting short paired end reads.\n")
            result = ruClient.download_reads({'read_libraries': reads_refs,
                                              'interleaved': 'false'})

            # combine outputs
            short_fwd_path = os.path.join(self.scratch, "short_fwd_"+str(uuid.uuid4())+".fastq")
            short_rev_path = os.path.join(self.scratch, "short_rev_"+str(uuid.uuid4())+".fastq")
            self.log(console, "Combining short paired end reads.\n")

            for reads_ref in reads_refs:
                files = result['files'][reads_ref]['files']
                self.log(console, 'files = '+pformat(files))

                if 'fwd' in files:
                    path = files['fwd']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_fwd_path
                    else:
                        cmd = 'cat '+path+' >> '+short_fwd_path
                    self.log(console, "command: "+cmd)
                    cmdProcess = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
                        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+reads_ref+' missing forward reads file')
                if 'rev' in files:
                    path = files['rev']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_rev_path
                    else:
                        cmd = 'cat '+path+' >> '+short_rev_path
                    self.log(console, "command: "+cmd)
                    cmdProcess = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
                        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+reads_ref+' missing reverse reads file')

        except Exception as e:
            raise ValueError('Unable to download short paired reads\n' + str(e))

        return short_fwd_path, short_rev_path

    # get short unpaired reads, and combine into one file
    def download_short_unpaired(self, console, token, wsname, short_unpaired_libraries):
        try:
            self.log(console, "Getting short unpaired reads.\n")
            ruClient = ReadsUtils(url=self.callbackURL, token=token)

            # first, unpack any ReadsSets into the actual SingleEndLibrary referencs
            reads_refs = []
            # object info
            try:
                wsClient = Workspace(self.workspaceURL, token=token)
            except Exception as e:
                raise ValueError("unable to instantiate wsClient. "+str(e))

            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I,
                WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)  # object_info tuple
            for lib in short_unpaired_libraries:
                try:
                    obj_id = {'ref': lib if '/' in lib else (wsname + '/' + lib)}
                    lib_obj_info = wsClient.get_object_info_new({'objects': [obj_id]})[0]
                    lib_obj_type = lib_obj_info[TYPE_I]
                    # remove trailing version
                    lib_obj_type = re.sub('-[0-9]+\.[0-9]+$', "", lib_obj_type)
                    lib_ref = str(lib_obj_info[WSID_I])+'/' + \
                        str(lib_obj_info[OBJID_I])+'/'+str(lib_obj_info[VERSION_I])
                    if lib_obj_type == 'KBaseSets.ReadsSet':
                        # unpack it
                        try:
                            setAPIClient = SetAPI(url=self.serviceWizardURL, token=token)
                            self.log(console, 'getting reads set '+lib_ref)
                            readsSet = setAPIClient.get_reads_set_v1(
                                {'ref': lib_ref, 'include_item_info': 1})
                        except Exception as e:
                            raise ValueError(
                                'SetAPI FAILURE: Unable to get read library set object: (' + lib_ref + ')\n' + str(e))
                        for readsLibrary in readsSet['data']['items']:
                            reads_refs.append(readsLibrary['ref'])
                    else:
                        # use other reads objects "as is"
                        reads_refs.append(lib_ref)
                except Exception as e:
                    raise ValueError(
                        'Unable to get read library object: (' + str(lib) + ')' + str(e))

            result = ruClient.download_reads({'read_libraries': reads_refs,
                                              'interleaved': 'false'})
            # combine outputs
            short_unpaired_path = os.path.join(
                self.scratch, "short_unpaired_"+str(uuid.uuid4())+".fastq")

            self.log(console, "Combining short unpaired reads.\n")

            for reads_ref in reads_refs:
                files = result['files'][reads_ref]['files']

                if 'fwd' in files:
                    path = files['fwd']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_unpaired_path
                    else:
                        cmd = 'cat '+path+' >> '+short_unpaired_path
                    self.log(console, "command: "+cmd)
                    cmdProcess = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
                        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+reads_ref+' missing forward reads file')

        except Exception as e:
            raise ValueError('Unable to download short unpaired reads\n' + str(e))
        return short_unpaired_path

    # get long reads
    def download_long(self, console, warnings, token, wsname, lib, min_long_read_length):
        try:
            # object info
            try:
                wsClient = Workspace(self.workspaceURL, token=token)
            except Exception as e:
                raise ValueError("unable to instantiate wsClient. "+str(e))

            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I,
                WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)  # object_info tuple

            obj_id = {'ref': lib if '/' in lib else (wsname + '/' + lib)}
            lib_obj_info = wsClient.get_object_info_new({'objects': [obj_id]})[0]
            lib_obj_type = lib_obj_info[TYPE_I]
            lib_obj_type = re.sub('-[0-9]+\.[0-9]+$', "", lib_obj_type)  # remove trailing version
            lib_ref = str(lib_obj_info[WSID_I])+'/' + \
                str(lib_obj_info[OBJID_I])+'/'+str(lib_obj_info[VERSION_I])
            if lib_obj_type == 'KBaseGenomes.ContigSet' or lib_obj_type == 'KBaseGenomeAnnotations.Assembly':
                # download using assembly util / data file util
                self.log(console, "Getting long reads (from contigs object).\n")
                auClient = AssemblyUtil(url=self.callbackURL, token=token)
                dfuClient = DataFileUtil(url=self.callbackURL, token=token)
                contigFile = auClient.get_assembly_as_fasta({'ref': lib_ref}).get('path')
                long_reads_path = dfuClient.unpack_file({'file_path': contig_file})['file_path']
                self.log(
                    warnings, "Warning:  Long reads are in FASTA format, so short read check was not performed.")

            else:
                ruClient = ReadsUtils(url=self.callbackURL, token=token)
                self.log(console, "Getting long reads (from reads library object).\n")
                result = ruClient.download_reads({'read_libraries': [lib_ref],
                                                  'interleaved': 'false'})
                long_reads_path = result['files'][lib_ref]['files']['fwd']
                [n_reads, n_reads_short] = self.filter_short_fastq(
                    console, long_reads_path, min_long_read_length)
                if (n_reads_short > 0):
                    self.log(warnings, "Warning:  Of "+str(n_reads)+" long reads, "+str(n_reads_short)+" are shorter than " +
                             str(min_long_read_length)+"; consider using the filtlong app to filter out shorter reads.")

        except Exception as e:
            raise ValueError('Unable to download long reads\n' + str(e))
        return long_reads_path

    # examine fastq files
    def filter_short_fastq(self, console, fastq_path, min_length):
        n_reads = 0
        n_reads_short = 0
        with open(fastq_path, 'r') as input_file_handle:
            for current_line in input_file_handle:
                if (current_line[0] == '@'):
                    # self.log(console, 'fastq header = '+current_line)
                    n_reads += 1
                    seq = next(input_file_handle)
                    if len(seq) < min_length:
                        n_reads_short += 1
                    next(input_file_handle)
                    next(input_file_handle)
            self.log(console, str(n_reads)+' long reads found, ' +
                     str(n_reads_short)+' under '+str(min_length)+' bp')
        return [n_reads, n_reads_short]

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.cfg = config
        self.cfg['SDK_CALLBACK_URL'] = os.environ['SDK_CALLBACK_URL']
        self.cfg['KB_AUTH_TOKEN'] = os.environ['KB_AUTH_TOKEN']
        self.callbackURL = self.cfg['SDK_CALLBACK_URL']
        self.serviceWizardURL = config['service-wizard']
        self.workspaceURL = config['workspace-url']
        self.shockURL = config['shock-url']
        self.scratch = os.path.abspath(config['scratch'])
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)
        self.appdir = os.path.abspath(config['appdir'])
        #END_CONSTRUCTOR
        pass

    def run_unicycler(self, ctx, params):
        """
        Run Unicycler
        :param params: instance of type "UnicyclerParams" (To run Unicycler,
           you need at least one short read paired end library, and optional
           unpaired reads (divided into short and long.  All reads of the
           same time must be combined into a single file. workspace_name -
           the name of the workspace from which to take input and store
           output. output_contigset_name - the name of the output contigset
           short_paired_libraries - a list of short, paired end reads
           libraries short_unpaired_libraries - a list of short, paired end
           reads libraries long_reads_libraries - a list of long reads
           @optional min_contig_length @optional num_linear_seqs @optional
           bridging_mode) -> structure: parameter "workspace_name" of String,
           parameter "output_contigset_name" of String, parameter
           "short_paired_libraries" of list of type "paired_lib" (The
           workspace object name of a PairedEndLibrary file, whether of the
           KBaseAssembly or KBaseFile type.), parameter
           "short_unpaired_libraries" of list of type "unpaired_lib" (The
           workspace object name of a SingleEndLibrary file, whether of the
           KBaseAssembly or KBaseFile type.), parameter "long_reads_library"
           of String, parameter "min_contig_length" of Long, parameter
           "num_linear_seqs" of Long, parameter "bridging_mode" of String
        :returns: instance of type "UnicyclerOutput" (Output parameters for
           Unicycler run. report_name - the name of the KBaseReport.Report
           workspace object. report_ref - the workspace reference of the
           report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_unicycler
        console = []
        warnings = []
        self.log(console, 'Running run_unicycler with params:\n{}'.format(
            json.dumps(params, indent=1)))
        token = self.cfg['KB_AUTH_TOKEN']

        # param checks
        required_params = ['workspace_name',
                           'output_contigset_name',
                           'min_contig_length',
                           'num_linear_seqs',
                           'bridging_mode']
        for required_param in required_params:
            if required_param not in params or params[required_param] is None:
                raise ValueError("Must define required param: '"+required_param+"'")

        # needs either short paired or long
        if ('short_paired_libraries' not in params or params['short_paired_libraries'] is None or len(params['short_paired_libraries']) == 0) and ('long_reads_library' not in params or params['long_reads_library'] is None):
            raise ValueError("Must define either short_paired_libraries or long_reads_library")

        # load provenance
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        if 'input_ws_objects' not in provenance[0]:
            provenance[0]['input_ws_objects'] = []

        if 'short_paired_libraries' in params and params['short_paired_libraries'] is not None and len(params['short_paired_libraries']) > 0:
            provenance[0]['input_ws_objects'].extend(params['short_paired_libraries'])
        if 'short_unpaired_libraries' in params and params['short_unpaired_libraries'] is not None and len(params['short_unpaired_libraries']) > 0:
            provenance[0]['input_ws_objects'].extend(params['short_unpaired_libraries'])
        if 'long_reads_library' in params and params['long_reads_library'] is not None:
            provenance[0]['input_ws_objects'].append(params['long_reads_library'])

        # build command line
        cmd = 'unicycler'

        # download, split, and recombine short paired libraries
        if 'short_paired_libraries' in params and params['short_paired_libraries'] is not None and len(params['short_paired_libraries']) > 0:
            short1, short2 = self.download_short_paired(
                console, token, params['workspace_name'], params['short_paired_libraries'])
            cmd += ' -1 '+short1+' -2 '+short2

        # download and combine short unpaired libraries
        if 'short_unpaired_libraries' in params and params['short_unpaired_libraries'] is not None and len(params['short_unpaired_libraries']) > 0:
            unpaired = self.download_short_unpaired(
                console, token, params['workspace_name'], params['short_unpaired_libraries'])
            cmd += ' -s '+unpaired

        # download long library
        if 'long_reads_library' in params and params['long_reads_library'] is not None:
            longLib = self.download_long(
                console, warnings, token, params['workspace_name'], params['long_reads_library'], params['min_long_read_length'])
            cmd += ' -l '+longLib

        # other params
        cmd += ' --min_fasta_length '+str(params['min_contig_length'])
        cmd += ' --linear_seqs '+str(params['num_linear_seqs'])
        cmd += ' --mode '+str(params['bridging_mode'])
        cmd += ' --keep 0'

        if ('no_correct' in params and (params['no_correct'] == 1)):
            cmd += ' --no_correct'

        # output directory
        outputDir = os.path.join(self.scratch, "unicycler_"+str(uuid.uuid4()))
        self.mkdir_p(outputDir)
        cmd += ' -o '+outputDir

        # run it
        self.log(console, "command: "+cmd)
        cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, shell=True)
        for line in cmdProcess.stdout:
            self.log(console, line.decode("utf-8").rstrip())
        cmdProcess.wait()
        if cmdProcess.returncode != 0:
            raise ValueError('Error running '+cmd)

        # save assembly
        try:
            contigsPath = os.path.join(outputDir, 'assembly.fasta')
            auClient = AssemblyUtil(url=self.callbackURL, token=token, service_ver='release')
            auClient.save_assembly_from_fasta(
                {'file': {'path': contigsPath},
                 'workspace_name': params['workspace_name'],
                 'assembly_name': params['output_contigset_name']})
        except Exception as e:
            raise ValueError('Error saving assembly\n' + str(e))

        # make report
        report_name, report_ref = self.generate_report(
            console, warnings, contigsPath, params, outputDir, params['workspace_name'])
        output = {'report_name': report_name,
                  'report_ref': report_ref}

        #END run_unicycler

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_unicycler return value ' +
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
        #END_STATUS
        return [returnVal]
