# -*- coding: utf-8 -*-
import re
import time
import os
import errno
import numpy as np
import zipfile
import subprocess
from pprint import pprint
import uuid
import copy
import json

from Workspace.WorkspaceClient import Workspace as Workspace
from KBaseReport.KBaseReportClient import KBaseReport
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
from kb_quast.kb_quastClient import kb_quast
from ReadsUtils.ReadsUtilsClient import ReadsUtils
from ReadsUtils.baseclient import ServerError


def log(message, prefix_newline=False):
    """Logging function, provides a hook to suppress or redirect log messages."""
    print(('\n' if prefix_newline else '') + '{0:.2f}'.format(time.time()) + ': ' + str(message))


def _mkdir_p(path):
    """
    _mkdir_p: make directory for given path
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


class SPAdesUtils:
    SPADES_VERSION = '3.13.0'
    SPADES_BIN = '/opt/SPAdes-' + SPADES_VERSION + '-Linux/bin'

    DISABLE_SPADES_OUTPUT = False  # should be False in production

    # Basic options
    PARAM_IN_SINGLE_CELL = 'single_cell'  # --sc
    PARAM_IN_METAGENOME = 'metagenomic'  # --meta
    PARAM_IN_PLASMID = 'plasmid'  # --plasmid
    PARAM_IN_RNA = 'rna'  # --rna
    PARAM_IN_IONTORRENT = 'iontorrent'  # --iontorrent

    # Pipeline options
    PARAM_IN_ONLY_ERROR_CORR = 'only-error-correction'  # --only-error-correction
    PARAM_IN_ONLY_ASSEMBLER = 'only-assembler'  # --only-assembler
    PARAM_IN_CAREFUL = 'careful'  # --careful
    PARAM_IN_CONTINUE = 'continue'  # --continue
    PARAM_IN_DISABLE_GZIP = 'disable-gzip-output'  # --disable-gzip-output

    # Input parameters
    PARAM_IN_WS = 'workspace_name'
    PARAM_IN_CS_NAME = 'output_contigset_name'
    PARAM_IN_PAIREDEND_READS = 'pairedEnd_reads'
    PARAM_IN_SINGLE_READS = 'single_reads'
    PARAM_IN_MATEPAIR_READS = 'mate_pair_reads'
    PARAM_IN_PACBIO_READS = 'pacbio_reads'
    PARAM_IN_NANO_READS = 'nanopore_reads'
    PARAM_IN_MIN_CONTIG_LENGTH = 'min_contig_length'
    PARAM_IN_KMER_SIZES = 'kmer_sizes'
    PARAM_IN_SKIP_ERR_CORRECT = 'skip_error_correction'
    PARAM_IN_DNA_SOURCE = 'dna_source'
    PARAM_IN_PIPELINE_OPTION = 'pipeline_options'

    INVALID_WS_OBJ_NAME_RE = re.compile('[^\\w\\|._-]')
    INVALID_WS_NAME_RE = re.compile('[^\\w:._-]')

    # private method definition----copied from MaSuRCA, should be rewritten to suit SPAdes
    def __init__(self, prj_dir, config):
        self.workspace_url = config['workspace-url']
        self.callback_url = config['SDK_CALLBACK_URL']
        self.token = config['KB_AUTH_TOKEN']
        if 'shock-url' in config:
            self.shock_url = config['shock-url']
        if 'handle-service-url' in config:
            self.handle_url = config['handle-service-url']

        self.ws_client = Workspace(self.workspace_url, token=self.token)
        self.ru = ReadsUtils(self.callback_url, token=self.token)
        self.au = AssemblyUtil(self.callback_url, token=self.token)
        self.kbr = KBaseReport(self.callback_url)
        self.kbq = kb_quast(self.callback_url)
        self.proj_dir = prj_dir

        self.spades_version = 'SPAdes-' + os.environ['SPADES_VERSION']

    def _has_long_reads(self, params):
        """
        _has_long_reads: check if a long reads input exists in the parameters
        """
        return (params.get(self.PARAM_IN_PACBIO_READS, None) or
                params.get(self.PARAM_IN_NANO_READS, None))

    def _get_kbreads_info(self, wsname, reads_refs):
        """
        _get_kbreads_info--from a set of given KBase reads refs, fetches the corresponding
        reads info with as interleaved fastq files and returns a list of reads data in the
        following structure:
        reads_data = {
                'fwd_file': path_to_fastq_file,
                'type': reads_type,  # ('interleaved', 'paired', or 'single')
                'seq_tech': sequencing_tech,
                'reads_ref': KBase object ref for downstream convenience,
                'reads_name': KBase object name for downstream convenience,
                'rev_file': path_to_fastq_file, #only if paired end
        }
        """
        obj_ids = []
        for r in reads_refs:
            if r:
                obj_ids.append({'ref': r if '/' in r else (wsname + '/' + r)})

        if not obj_ids:
            return []

        ws_info = self.ws_client.get_object_info_new({'objects': obj_ids})
        reads_params = []

        reftoname = {}
        for wsi, oid in zip(ws_info, obj_ids):
            ref = oid['ref']
            reads_params.append(ref)
            obj_name = wsi[1]
            reftoname[ref] = wsi[7] + '/' + obj_name

        typeerr = ('Supported types: KBaseFile.SingleEndLibrary ' +
                   'KBaseFile.PairedEndLibrary ' +
                   'KBaseAssembly.SingleEndLibrary ' +
                   'KBaseAssembly.PairedEndLibrary')
        try:
            reads = self.ru.download_reads({
                        'read_libraries': reads_params,
                        'interleaved': 'false'
                        })['files']
        except ServerError as se:
            log('logging stacktrace from dynamic client error')
            log(se.data)
            if typeerr in se.message:
                prefix = se.message.split('.')[0]
                raise ValueError(
                    prefix + '. Only the types ' +
                    'KBaseAssembly.SingleEndLibrary ' +
                    'KBaseAssembly.PairedEndLibrary ' +
                    'KBaseFile.SingleEndLibrary ' +
                    'and KBaseFile.PairedEndLibrary are supported')
            else:
                raise

        # log('Downloaded reads data from KBase:\n' + pformat(reads))
        reads_data = []
        for ref in reads_refs:
            reads_name = reftoname[ref]
            f = reads[ref]['files']
            seq_tech = reads[ref]['sequencing_tech']
            rds_info = {
                'fwd_file': f['fwd'],
                'reads_ref': ref,
                'type': f['type'],
                'seq_tech': seq_tech,
                'reads_name': reads_name
            }
            if f.get('rev', None):
                rds_info['rev_file'] = f['rev']
            reads_data.append(rds_info)

        return reads_data

    def _generate_output_file_list(self, out_dir):
        """
        _generate_output_file_list: zip result files and generate file_links for report
        """
        log('start packing result files')

        output_files = list()

        output_directory = os.path.join(self.proj_dir, str(uuid.uuid4()))
        _mkdir_p(output_directory)
        masurca_output = os.path.join(output_directory, 'masurca_output.zip')
        self._zip_folder(out_dir, masurca_output)

        output_files.append({'path': masurca_output,
                             'name': os.path.basename(masurca_output),
                             'label': os.path.basename(masurca_output),
                             'description': 'Output file(s) generated by MaSuRCA'})

        return output_files

    def _zip_folder(self, folder_path, output_path):
        """
        _zip_folder: Zip the contents of an entire folder (with that folder included
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
        # with zipfile.ZipFile(output_path, "r") as f:
        #    print 'Checking the zipped file......\n'
        #    for info in f.infolist():
        #        print info.filename, info.date_time, info.file_size, info.compress_size

    def _load_stats(self, input_file_name):
        log('Starting conversion of FASTA to KBaseGenomeAnnotations.Assembly')
        log('Building Object.')
        if not os.path.isfile(input_file_name):
            raise Exception('The input file name {0} is not a file!'.format(input_file_name))
        with open(input_file_name, 'r') as input_file_handle:
            contig_id = None
            sequence_len = 0
            fasta_dict = dict()
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
                        fasta_dict[contig_id] = sequence_len
                        sequence_len = 0
                    fasta_header = current_line.replace('>', '').strip()
                    try:
                        contig_id = fasta_header.strip().split(' ', 1)[0]
                    except (IndexError, ValueError, KeyError):
                        contig_id = fasta_header.strip()
                else:
                    sequence_len += len(re.sub(pattern, '', current_line))
        # wrap up last fasta sequence
        if not first_header_found:
            raise Exception("There are no contigs in this file")
        else:
            fasta_dict[contig_id] = sequence_len
        return fasta_dict

    def _check_ref_type(self, ref, allowed_types):
        """
        Validates the object type of ref against the list of allowed types. If it passes, this
        returns True, otherwise False.
        Really, all this does is verify that at least one of the strings in allowed_types is
        a substring of the ref object type name.
        Ex1:
        ref = "KBaseGenomes.Genome-4.0"
        allowed_types = ["assembly", "KBaseFile.Assembly"]
        returns False
        Ex2:
        ref = "KBaseGenomes.Genome-4.0"
        allowed_types = ["assembly", "genome"]
        returns True
        """
        obj_type = self._get_object_type(ref).lower()
        for t in allowed_types:
            if t.lower() in obj_type:
                return True
        return False

    def _get_object_type(self, ref):
        """
        Fetches and returns the typed object name of ref from the given workspace url.
        If that object doesn't exist, or there's another Workspace error, this raises a
        RuntimeError exception.
        """
        info = self.ws_client.get_object_info3({'objects': [{'ref': ref}]})
        obj_info = info.get('infos', [[]])[0]
        if len(obj_info) == 0:
            raise RuntimeError("An error occurred while fetching type info from the Workspace. "
                               "No information returned for reference {}".format(ref))
        return obj_info[2]

    def _get_fasta_from_assembly(self, assembly_ref):
        """
        From an assembly or contigset, this uses a data file to build a FASTA file
        and return the path to it.
        """
        allowed_types = ['KBaseFile.Assembly',
                         'KBaseGenomeAnnotations.Assembly',
                         'KBaseGenomes.ContigSet']
        if not self._check_ref_type(assembly_ref, allowed_types):
            raise ValueError(
                "The reference {} cannot be used to fetch a FASTA file".format(assembly_ref))
        au = AssemblyUtil(self.callback_url)
        return au.get_assembly_as_fasta({'ref': assembly_ref})

    def _fetch_reads_from_reference(ref, callback_url):
        """
        Fetch a FASTQ file (or 2 for paired-end) from a reads reference.
        Returns the following structure:
        {
            "style": "paired", "single", or "interleaved",
            "file_fwd": path_to_file,
            "file_rev": path_to_file, only if paired end,
            "object_ref": reads reference for downstream convenience.
        }
        """
        try:
            print("Fetching reads from object {}".format(ref))
            reads_client = ReadsUtils(callback_url)
            reads_dl = reads_client.download_reads({
                "read_libraries": [ref],
                "interleaved": "false"
            })
            pprint(reads_dl)
            reads_files = reads_dl['files'][ref]['files']
            ret_reads = {
                "object_ref": ref,
                "style": reads_files["type"],
                "file_fwd": reads_files["fwd"]
            }
            if reads_files.get("rev", None) is not None:
                ret_reads["file_rev"] = reads_files["rev"]

            return ret_reads
        except Exception:
            print("Unable to fetch a file from expected reads object {}".format(ref))
            raise

    # end of private methods

    # public method definitions

    def check_spades_params(self, params):
        """
        check_spades_params: checks params passed to run_HybridSPAdes method and set default values
        """
        # log('Start validating run_HybridSPAdes parameters:\n{}'.format(
        # json.dumps(params, indent=1)))

        # check for mandatory parameters
        if params.get(self.PARAM_IN_WS, None) is None:
            raise ValueError('Parameter {} is mandatory!'.format(self.PARAM_IN_WS))
        if self.INVALID_WS_NAME_RE.search(params[self.PARAM_IN_WS]):
            raise ValueError('Invalid workspace name: {}.'.format(
                             params[self.PARAM_IN_WS]))

        if params.get(self.PARAM_IN_CS_NAME, None) is None:
            raise ValueError('Parameter {} is mandatory!'.format(self.PARAM_IN_CS_NAME))
        if self.INVALID_WS_OBJ_NAME_RE.search(params[self.PARAM_IN_CS_NAME]):
            raise ValueError('Invalid workspace object name: {}.'.format(
                             params[self.PARAM_IN_CS_NAME]))

        if (params.get(self.PARAM_IN_PAIREDEND_READS, None) is None and
                params.get(self.PARAM_IN_SINGLE_READS, None) is None and
                params.get(self.PARAM_IN_MATEPAIR_READS, None) is None):
            raise ValueError('At least one of parameters {}, {} and {} is required.'.format(
                             self.PARAM_IN_SINGLE_READS,
                             self.PARAM_IN_PAIREDEND_READS,
                             self.PARAM_IN_MATEPAIR_READS))

        if ((params.get(self.PARAM_IN_SINGLE_READS) and
                type(params[self.PARAM_IN_SINGLE_READS]) != list) or
                (params.get(self.PARAM_IN_PAIREDEND_READS) and
                    type(params[self.PARAM_IN_PAIREDEND_READS]) != list) or
                (params.get(self.PARAM_IN_MATEPAIR_READS) and
                    type(params[self.PARAM_IN_MATEPAIR_READS]) != list)):
            raise ValueError('Input reads must be a list.')

        if self.PARAM_IN_MIN_CONTIG_LENGTH in params:
            if not isinstance(params[self.PARAM_IN_MIN_CONTIG_LENGTH], int):
                raise ValueError('{} must be of type int.'.format(self.PARAM_IN_MIN_CONTIG_LENGTH))

        if params.get(self.PARAM_IN_KMER_SIZES, None):
            print("KMER_SIZES: " + ",".join(str(num) for num in params[self.PARAM_IN_KMER_SIZES]))
        if params.get(self.PARAM_IN_SKIP_ERR_CORRECT, None):
            print("SKIP ERR CORRECTION: " + str(params[self.PARAM_IN_SKIP_ERR_CORRECT]))

        # check for basic option parameters
        if params.get(self.PARAM_IN_DNA_SOURCE, None):
            dna_src = params[self.PARAM_IN_DNA_SOURCE]
            if dna_src not in [self.PARAM_IN_SINGLE_CELL,
                               self.PARAM_IN_METAGENOME,
                               self.PARAM_IN_PLASMID,
                               self.PARAM_IN_RNA,
                               self.PARAM_IN_IONTORRENT]:
                params[self.PARAM_IN_DNA_SOURCE] = None
        else:
            params[self.PARAM_IN_DNA_SOURCE] = None

        params['basic_options'] = [' '.join(['-o', self.proj_dir])]  # a list of basic options
        dna_src = params.get(self.PARAM_IN_DNA_SOURCE)
        if dna_src == self.PARAM_IN_SINGLE_CELL:
            params['basic_options'].append('--sc')
        elif dna_src == self.PARAM_IN_METAGENOME:
            params['basic_options'].append('--meta')
        elif dna_src == self.PARAM_IN_PLASMID:
            params['basic_options'].append('--plasmid')
        elif dna_src == self.PARAM_IN_RNA:
            params['basic_options'].append('--rna')
        elif dna_src == self.PARAM_IN_IONTORRENT:
            params['basic_options'].append('--iontorrent')

        # check for pipeline option parameters
        if params.get(self.PARAM_IN_PIPELINE_OPTION, None):
            pipe_opt = params[self.PARAM_IN_PIPELINE_OPTION]
            if pipe_opt not in [self.PARAM_IN_ONLY_ERROR_CORR,
                                self.PARAM_IN_ONLY_ASSEMBLER,
                                self.PARAM_IN_CONTINUE,
                                self.PARAM_IN_DISABLE_GZIP,
                                self.PARAM_IN_CAREFUL]:
                params[self.PARAM_IN_PIPELINE_OPTION] = self.PARAM_IN_CAREFUL
        else:
            params[self.PARAM_IN_PIPELINE_OPTION] = self.PARAM_IN_CAREFUL

        pipe_opt = params.get(self.PARAM_IN_PIPELINE_OPTION)
        if pipe_opt == self.PARAM_IN_ONLY_ERROR_CORR:
            params[self.PARAM_IN_PIPELINE_OPTION].append('--only-error-correction')
        elif pipe_opt == self.PARAM_IN_ONLY_ASSEMBLER:
            params[self.PARAM_IN_PIPELINE_OPTION].append('--only-assembler')
        elif pipe_opt == self.PARAM_IN_CONTINUE:
            params[self.PARAM_IN_PIPELINE_OPTION].append('--continue')
        elif pipe_opt == self.PARAM_IN_DISABLE_GZIP:
            params[self.PARAM_IN_PIPELINE_OPTION].append('--disable-gzip-output')
        else:
            params[self.PARAM_IN_PIPELINE_OPTION].append('--careful')

        if params.get('create_report', None) is None:
            params['create_report'] = 0

        return params

    # copied from MaSuRCA, should be rewritten to suit SPAdes
    def generate_report(self, contig_file_name, params, out_dir, wsname):
        log('Generating and saving report')

        contig_file_with_path = os.path.join(out_dir, contig_file_name)
        fasta_stats = self._load_stats(contig_file_with_path)
        lengths = [fasta_stats[contig_id] for contig_id in fasta_stats]

        assembly_ref = params[self.PARAM_IN_WS] + '/' + params[self.PARAM_IN_CS_NAME]

        report_text = ''
        report_text += 'MaSuRCA results saved to: ' + wsname + '/' + out_dir + '\n'
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
        print('Running QUAST')
        quastret = self.kbq.run_QUAST(
            {'files': [{'path': contig_file_with_path, 'label': params[self.PARAM_IN_CS_NAME]}]})

        output_files = self._generate_output_file_list(out_dir)

        print('Saving report')
        report_output = self.kbr.create_extended_report(
            {'message': report_text,
             'objects_created': [{'ref': assembly_ref, 'description': 'Assembled contigs'}],
             'direct_html_link_index': 0,
             'file_links': output_files,
             'html_links': [{'shock_id': quastret['shock_id'],
                             'name': 'report.html',
                             'label': 'QUAST report'}
                            ],
             'report_object_name': 'kb_masurca_report_' + str(uuid.uuid4()),
             'workspace_name': params[self.PARAM_IN_WS]})
        report_name = report_output['name']
        report_ref = report_output['ref']
        return report_name, report_ref

    def get_hybrid_reads_info(self, input_params):
        """
        get_hybrid_reads_info--from a list of ReadsParams structures fetches the corresponding
        reads info with the ReadsParams[lib_ref]
        returns a tuple of five reads data each is a list of the following structure:
        reads_data = {
                'fwd_file': path_to_fastq_file,
                'orientation': (default value is "fr" (forward-reverse) for paired-end libraries
                                "rf" (reverse-forward) for mate-pair libraries), None for others
                'lib_type': ("paired-end", "mate-pairs", "hq-mate-pairs", "single", "pacbio",
                              "nanopore", "sanger", "trusted-contigs", "untrusted-contigs"),
                'type': reads_type, # 'interleaved', 'paired', or 'single'
                'seq_tech': sequencing_tech,
                'reads_ref': KBase object ref for downstream convenience,
                'reads_name': KBase object name for downstream convenience,
                'rev_file': path_to_fastq_file  # only if paired end
        }
        """
        rds_params = copy.deepcopy(input_params)
        wsname = rds_params[self.PARAM_IN_WS]

        # single end reads grouped params
        rds_refs = []
        se_rds_data = []

        if rds_params.get(self.PARAM_IN_SINGLE_READS, None):
            se_libs = rds_params[self.PARAM_IN_SINGLE_READS]
            for se_lib in se_libs:
                if se_lib.get('lib_ref', None):
                    rds_refs.append(se_lib['lib_ref'])
            se_rds_data = self._get_kbreads_info(wsname, rds_refs)

            for se_lib in se_libs:
                for rds in se_rds_data:
                    if ('lib_ref' in se_lib and se_lib['lib_ref'] == rds['reads_ref']):
                        se_lib['orientation'] = None
                        rds['orientation'] = None
                        se_lib['lib_type'] = 'single'
                        rds['lib_type'] = se_lib['lib_type']

        # pairedEnd reads grouped params
        rds_refs = []
        pe_rds_data = []

        if rds_params.get(self.PARAM_IN_PAIREDEND_READS, None):
            pe_libs = rds_params[self.PARAM_IN_PAIREDEND_READS]
            for pe_lib in pe_libs:
                if pe_lib.get('lib_ref', None):
                    rds_refs.append(pe_lib['lib_ref'])
            pe_rds_data = self._get_kbreads_info(wsname, rds_refs)

            for pe_lib in pe_libs:
                for rds in pe_rds_data:
                    if ('lib_ref' in pe_lib and pe_lib['lib_ref'] == rds['reads_ref']):
                        if pe_lib.get('orientation', None) is None:
                            pe_lib['orientation'] = 'fr'
                        rds['orientation'] = pe_lib['orientation']
                        if pe_lib.get('lib_type', None) is None:
                            pe_lib['lib_type'] = 'paired-end'
                        rds['lib_type'] = pe_lib['lib_type']

        # mate-pair reads grouped params
        rds_refs = []
        mp_rds_data = []

        if rds_params.get(self.PARAM_IN_MATEPAIR_READS, None):
            mp_libs = rds_params[self.PARAM_IN_MATEPAIR_READS]
            for mp_lib in mp_libs:
                if mp_lib.get('lib_ref', None):
                    rds_refs.append(mp_lib['lib_ref'])
            mp_rds_data = self._get_kbreads_info(wsname, rds_refs)

            for mp_lib in mp_libs:
                for rds in mp_rds_data:
                    if ('lib_ref' in mp_lib and mp_lib['lib_ref'] == rds['reads_ref']):
                        if mp_lib.get('orientation', None) is None:
                            mp_lib['orientation'] = 'rf'
                        rds['orientation'] = mp_lib['orientation']
                        if mp_lib.get('lib_type', None) is None:
                            mp_lib['lib_type'] = 'mate-pairs'
                        rds['lib_type'] = mp_lib['lib_type']

        # PacBio reads grouped params
        rds_refs = []
        pb_rds_data = []

        if rds_params.get(self.PARAM_IN_PACBIO_READS, None):
            pb_libs = rds_params[self.PARAM_IN_PACBIO_READS]
            for pb_lib in pb_libs:
                if pb_lib.get('lib_ref', None):
                    rds_refs.append(pb_lib['lib_ref'])
            pb_rds_data = self._get_kbreads_info(wsname, rds_refs)

            for pb_lib in pb_libs:
                for rds in pb_rds_data:
                    if ('lib_ref' in pb_lib and pb_lib['lib_ref'] == rds['reads_ref']):
                        pb_lib['orientation'] = None
                        rds['orientation'] = None
                        if pb_lib.get('lib_type', None) is None:
                            pb_lib['lib_type'] = 'pacbio'
                        rds['lib_type'] = pb_lib['lib_type']

        # Nanopore reads grouped params
        rds_refs = []
        np_rds_data = []

        if rds_params.get(self.PARAM_IN_NANO_READS, None):
            np_libs = rds_params[self.PARAM_IN_NANO_READS]
            for np_lib in np_libs:
                if np_lib.get('lib_ref', None):
                    rds_refs.append(np_lib['lib_ref'])
            np_rds_data = self._get_kbreads_info(wsname, rds_refs)

            for np_lib in np_libs:
                for rds in np_rds_data:
                    if ('lib_ref' in np_lib and np_lib['lib_ref'] == rds['reads_ref']):
                        np_lib['orientation'] = None
                        rds['orientation'] = np_lib['orientation']
                        if np_lib.get('lib_type', None) is None:
                            np_lib['lib_type'] = 'nanopore'
                        rds['lib_type'] = np_lib['lib_type']

        return (se_rds_data, pe_rds_data, mp_rds_data, pb_rds_data, np_rds_data)

    def construct_yaml_dataset_file(self, se_libs=[], pe_libs=[], mp_libs=[],
                                    pb_libs=None, np_libs=None):
        """
        construct_yaml_dataset_file: Specifying input data with YAML data set file (advanced)
        An alternative way to specify an input data set for SPAdes is to create a YAML
        data set file.
        By using a YAML file you can provide an unlimited number of paired-end, mate-pair
        and unpaired libraries. Basically, YAML data set file is a text file, in which input
        libraries are provided as a comma-separated list in square brackets. Each library is
        provided in braces as a comma-separated list of attributes.

        The following attributes are available:

            - orientation ("fr", "rf", "ff")
            - type ("paired-end", "mate-pairs", "hq-mate-pairs", "single", "pacbio", "nanopore",
                "sanger", "trusted-contigs", "untrusted-contigs")
            - interlaced reads (comma-separated list of files with interlaced reads)
            - left reads (comma-separated list of files with left reads)
            - right reads (comma-separated list of files with right reads)
            - single reads (comma-separated list of files with single reads or unpaired reads from
                paired library)
            - merged reads (comma-separated list of files with merged reads)

        To properly specify a library you should provide its type and at least one file with reads.
        For ONT, PacBio, Sanger and contig libraries you can provide only single reads. Orientation
        is an optional attribute. Its default value is "fr" (forward-reverse) for paired-end
        libraries and "rf" (reverse-forward) for mate-pair libraries.

        The value for each attribute is given after a colon. Comma-separated lists of files should
        be given in square brackets.
        For each file you should provide its full path in double quotes. Make sure that files with
        right reads are given in the same order as corresponding files with left reads.

        For example, if you have one paired-end library splitted into two pairs of files:
            lib_pe1_left_1.fastq
            lib_pe1_right_1.fastq
            lib_pe1_left_2.fastq
            lib_pe1_right_2.fastq

        one mate-pair library:
            lib_mp1_left.fastq
            lib_mp1_right.fastq

        and PacBio CCS and CLR reads:
            pacbio_ccs.fastq
            pacbio_clr.fastq

        YAML file should look like this:
        ------------------------------------------------
        [
            {
                orientation: "fr",
                type: "paired-end",
                right reads: [
                "/FULL_PATH_TO_DATASET/lib_pe1_right_1.fastq",
                "/FULL_PATH_TO_DATASET/lib_pe1_right_2.fastq"
                ],
                left reads: [
                "/FULL_PATH_TO_DATASET/lib_pe1_left_1.fastq",
                "/FULL_PATH_TO_DATASET/lib_pe1_left_2.fastq"
                ]
            },
            {
                orientation: "rf",
                type: "mate-pairs",
                right reads: [
                "/FULL_PATH_TO_DATASET/lib_mp1_right.fastq"
                ],
                left reads: [
                "/FULL_PATH_TO_DATASET/lib_mp1_left.fastq"
                ]
            },
            {
                type: "single",
                single reads: [
                "/FULL_PATH_TO_DATASET/pacbio_ccs.fastq"
                ]
            },
            {
                type: "pacbio",
                single reads: [
                "/FULL_PATH_TO_DATASET/pacbio_clr.fastq"
                ]
            }
        ]
        ------------------------------------------------

        Once you have created a YAML file save it with .yaml extension (e.g. as my_data_set.yaml)
        and run SPAdes using the --dataset option:
        e.g., <SPAdes_bin_dir>/spades.py --dataset <your YAML file> -o spades_output

        """
        # STEP 1: get the working folder housing the config.txt file and the masurca results
        yaml_file_path = os.path.join(self.proj_dir, 'input_data_set.yaml')

        # STEP 2: construct and save the 'input_data_set.yaml' file
        # generate the object array
        input_data_set = []

        if se_libs and type(se_libs) == list and se_libs != []:
            single_reads_fqs = []
            for se in se_libs:
                single_reads_fqs.append(se['fwd_file'])

            input_data_set.append({
                "type": "single",
                "single reads": single_reads_fqs
            })

        if pe_libs and type(pe_libs) == list and pe_libs != []:
            right_reads_fqs = []
            left_reads_fqs = []
            for pe in pe_libs:
                right_reads_fqs.append(pe['fwd_file'])
                if pe.get('rev_file', None):
                    left_reads_fqs.append(pe['rev_file'])

            input_data_set.append({
                "orientation": "fr",
                "type": "paired-end",
                "right reads": right_reads_fqs,
                "left reads": left_reads_fqs
            })

        if mp_libs and type(mp_libs) == list and mp_libs != []:
            right_reads_fqs = []
            left_reads_fqs = []
            for mp in mp_libs:
                right_reads_fqs.append(mp['fwd_file'])
                if mp.get('rev_file', None):
                    left_reads_fqs.append(mp['rev_file'])

            input_data_set.append({
                "orientation": "rf",
                "type": "mate-pairs",
                "right reads": right_reads_fqs,
                "left reads": left_reads_fqs
            })

        if pb_libs and type(pb_libs) == list and pb_libs != []:
            single_reads_fqs = []
            pb_type = 'single'  # for lib_type = 'pacbioccs'
            for pb in pb_libs:
                single_reads_fqs.append(pb['fwd_file'])
            if pb_libs[0]['lib_type'] == 'pacbio':
                pb_type = 'pacbio'

            input_data_set.append({
                "type": pb_type,
                "single reads": single_reads_fqs
            })

        if np_libs and type(np_libs) == list and np_libs != []:
            single_reads_fqs = []
            np_type = 'single'
            for npr in np_libs:
                single_reads_fqs.append(npr['fwd_file'])

            input_data_set.append({
                "type": np_type,
                "single reads": single_reads_fqs
            })

        pprint(input_data_set)
        try:
            with open(yaml_file_path, 'w') as yaml_file:
                json.dump(input_data_set, yaml_file)
        except IOError as ioerr:
            log('Creation of the {} file raised error:\n'.format(yaml_file_path))
            pprint(ioerr)
            return ''
        else:
            return yaml_file_path

    def run_assemble(self, yaml_file, basic_opts=None, pipeline_opts=['--careful']):
        exit_code = 1
        if os.path.isfile(yaml_file):
            log("The input data set yaml file exists at {}\n".format(yaml_file))
            f_dir, f_nm = os.path.split(yaml_file)
            log("The working directory is {}\n".format(f_dir))

            a_cmd = [os.path.join(self.SPADES_BIN, 'spades.py')]
            a_cmd.append(' '.join(['--dataset', yaml_file]))

            if not basic_opts:
                basic_opts = [' '.join(['-o', self.proj_dir])]
            if type(basic_opts) == list and basic_opts != []:
                a_cmd.extend(basic_opts)

            if pipeline_opts:
                if type(pipeline_opts) == list and pipeline_opts != []:
                    a_cmd.extend(pipeline_opts)

            log("The assembling command is {}\n".format(' '.join(a_cmd)))
            p = subprocess.Popen(a_cmd, cwd=f_dir, shell=False)
            exit_code = p.wait()
            log('Return code: ' + str(exit_code))

            if p.returncode != 0:
                raise ValueError('Error running spades.py, return code: ' +
                                 str(p.returncode) + '\n')
            else:
                exit_code = p.returncode
        else:
            log("The input data set yaml file {} is not found.".format(yaml_file))
        return exit_code

    # copied from MaSuRCA, should be rewritten to suit SPAdes
    def save_assembly(self, contig_fa, wsname, a_name):
        if os.path.isfile(contig_fa):
            log('Uploading FASTA file to Assembly...')
            self.au.save_assembly_from_fasta(
                            {'file': {'path': contig_fa},
                             'workspace_name': wsname,
                             'assembly_name': a_name})
        else:
            log("The contig file {} is not found.".format(contig_fa))

    # end of public methods
