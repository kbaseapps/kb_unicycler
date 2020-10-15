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
from pprint import pformat

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
    GIT_COMMIT_HASH = "42fb1012a98ab1374bd9f4ed12429539ae1c221c"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.cfg = config
        self.cfg['SDK_CALLBACK_URL'] = os.environ['SDK_CALLBACK_URL']
        self.cfg['KB_AUTH_TOKEN'] = os.environ['KB_AUTH_TOKEN']
        self.callbackURL = self.cfg['SDK_CALLBACK_URL']
        self.log('Callback URL: ' + self.callbackURL)
        self.serviceWizardURL = config['service-wizard']
        self.workspaceURL = config[self.URL_WS]
        self.shockURL = config[self.URL_SHOCK]
        self.catalogURL = config[self.URL_KB_END] + '/catalog'
        self.scratch = os.path.abspath(config['scratch'])
        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)
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
        self.log('Running run_unicycler with params:\n{}'.format(
                 json.dumps(params, indent=1)))

        # param checks
        required_params = [ 'workspace_name',
                            'output_contigset_name',
                            'short_paired_libraries',
                            'min_contig_length',
                            'num_linear_seqs',
                            'bridging_mode' ]
        for required_param in required_params:
            if required_param not in params or params[required_param] == None:
                raise ValueError ("Must define required param: '"+required_param+"'")

        # load provenance
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        provenance[0]['input_ws_objects'].extend(params['short_paired_libraries'])
        if 'short_unpaired_libraries' in params:
            provenance[0]['input_ws_objects'].extend(params['short_unpaired_libraries'])
        if 'long_reads_library' in params:
            provenance[0]['input_ws_objects'].append(params['long_reads_library'])

        # download, split, and recombine short paired libraries
        [short1, short2] = download_short_paired(console, token, params['short_paired_libraries'])
        # build command line
        cmd = 'unicycler -1 '+short1+' -2 '+short2
        
        # download and combine short unpaired libraries
        if 'short_unpaired_libraries' in params:
            unpaired = download_short_unpaired(console, token, params['short_unpaired_libraries'])
            cmd += ' -s '+unpaired

        # download long library
        if 'long_reads_library' in params:
            longLib = download_long(console, token, params['long_reads_library'])
            cmd += ' -l '+longLib

        # other params
        cmd += ' --min_fasta_length '+params['min_contig_length']
        cmd += ' --linear_seqs '+params['num_linear_seqs']
        cmd += ' --mode '+params['bridging_mode']
        cmd += ' --keep 0'

        # output directory
        outputDir = os.path.join(self.scratch,"unicycler_"+str(uuid.uuid4()))
        cmd += ' -o '+outputDir

        # run it
        self.log(console,"command: "+cmd)
        cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        cmdProcess.wait()
        if cmdProcess.returncode != 0:
	    raise ValueError('Error running '+cmd)

        # save assembly
        try:
            auClient = AssemblyUtil(self.callbackURL, token=self.token, service_ver='release')
            auClient.save_assembly_from_fasta(
                {'file': {'path': os.join(outputDir,'assembly.fa')},
                 'workspace_name': params['workspace_name'],
                 'assembly_name': params['output_contigset_name']})
        except Exception as e:
            raise ValueError('Error saving assembly\n' + str(e))

        # make report
        report_name, report_ref = generate_report(os.join(outputDir,'assembly.fa'), params, outputDir, params['workspace_name'])
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
