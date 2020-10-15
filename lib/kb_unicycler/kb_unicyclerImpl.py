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
    GIT_COMMIT_HASH = "54b34e7c5ad78e7e6543f4bcf790406c68d5bd9d"

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

    # get short paired reads, and combine into forward and reverse files
    def download_short_paired(self, console, token, short_paired_libraries):
        try:
            ruClient = RUClient(url=self.callback_url, token=token)
            
            # first, unpack any ReadsSets into the actual PairedEndLibrary referencs
            reads_refs = []
            # object info
            try:
                wsClient = Workspace(self.workspaceURL, token=token)
            except Exception as e:
                raise ValueError("unable to instantiate wsClient. "+str(e))
            
            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)  # object_info tuple           
            for lib_ref in params['short_paired_libraries']:
                try:
                    lib_obj_info = wsClient.get_object_info_new({'objects':[{'ref':lib_ref}]})[0]
                    lib_obj_type = lib_obj_info[TYPE_I]
                    lib_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", lib_obj_type)  # remove trailing version
                    if lib_obj_type == 'KBaseSets.ReadsSet':
                        # unpack it
                        try:
                            setAPIClient = SetAPI(url=self.serviceWizardURL, token=ctx['token'])
                            self.log(console,'getting reads set '+lib_ref)
                            readsSet = setAPIClient.get_reads_set_v1({'ref':lib_ref,'include_item_info':1})
                        except Exception as e:
                            raise ValueError('SetAPI FAILURE: Unable to get read library set object: (' + lib_ref+ ')\n' + str(e))
                        for readsLibrary in readsSet['data']['items']:
                            reads_refs.append(readsLibrary['ref'])
                    else:
                        # use other reads objects "as is"
                        reads_refs.append(lib_ref)
                except Exception as e:
                    raise ValueError('Unable to get read library object: (' + str(lib_ref) +')' + str(e))

            # download all reads refs in one call, in separate files
            self.log(console,"Getting short paired end reads.\n");
            result = ruClient.download_reads ({'read_libraries': reads_refs,
                                               'interleaved': 'false'})
            
            # combine outputs
            short_fwd_path = os.path.join(self.scratch,"short_fwd_"+str(uuid.uuid4())+".fastq")
            short_rvs_path = os.path.join(self.scratch,"short_rvs_"+str(uuid.uuid4())+".fastq")
            self.log(console,"Combining short paired end reads.\n");

            for reads_ref in reads_refs:
                files = result['files'][reads_ref]['files']

                if 'fwd' in files:
                    path = files['fwd']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_fwd_path
                    else:
                        cmd = 'cat '+path+' >> '+short_fwd_path
                    self.log(console,"command: "+cmd)
                    cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
		        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+short_paired_library+' missing forward reads file')
                if 'rvs' in files:
                    path = files['rvs']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_rvs_path
                    else:
                        cmd = 'cat '+path+' >> '+short_rvs_path
                    self.log(console,"command: "+cmd)
                    cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
		        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+short_paired_library+' missing reverse reads file')

        except Exception as e:
            raise ValueError('Unable to download short paired reads\n' + str(e))
        
        return [short_fwd_path, short_rvs_path]

    # get short paired reads, and combine into one file
    def download_short_unpaired(self, console, token, short_unpaired_libraries):
        try:
            self.log(console,"Getting short unpaired reads.\n");
            ruClient = RUClient(url=self.callback_url, token=token)
            result = ruClient.download_reads ({'read_libraries': short_unpaired_libraries,
                                               'interleaved': 'false'})
            # combine outputs
            short_unpaired_path = os.path.join(self.scratch,"short_unpaired_"+str(uuid.uuid4())+".fastq")
                                       
            self.log(console,"Combining short unpaired reads.\n");

            for short_unpaired_library in short_unpaired_libraries:
                files = result['files'][short_unpaired_library]['files']

                if 'fwd' in files:
                    path = files['fwd']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_unpaired_path
                    else:
                        cmd = 'cat '+path+' >> '+short_unpaired_path
                    self.log(console,"command: "+cmd)
                    cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
		        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+short_unpaired_library+' missing forward reads file')

        except Exception as e:
            raise ValueError('Unable to download short unpaired reads\n' + str(e))
        return short_unpaired_path

    # get long reads
    def download_long(self, console, token, lib_ref):
        try:
            # object info
            try:
                wsClient = Workspace(self.workspaceURL, token=token)
            except Exception as e:
                raise ValueError("unable to instantiate wsClient. "+str(e))

            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)  # object_info tuple           
            try:
                lib_obj_info = wsClient.get_object_info_new({'objects':[{'ref':lib_ref}]})[0]
                lib_obj_type = lib_obj_info[TYPE_I]
                lib_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", lib_obj_type)  # remove trailing version
                if lib_obj_type == 'KBaseGenomes.ContigSet' or lib_obj_type == 'KBaseGenomeAnnotations.Assembly':
                    # download using assembly util / data file util
                    auClient = 
                    
            ruClient = RUClient(url=self.callback_url, token=token)
            self.log(console,"Getting long reads.\n");
            result = ruClient.download_reads ({'read_libraries': [long_library],
                                               'interleaved': 'false'
            })

            long_reads_path = os.path.join(self.scratch,"long_reads_"+str(uuid.uuid4())+".fastq")

            for short_unpaired_library in short_unpaired_libraries:
                files = result['files'][short_unpaired_library]['files']

                if 'fwd' in files:
                    path = files['fwd']
                    if path.endswith('.gz'):
                        cmd = 'gzip -dc '+path+' >> '+short_unpaired_path
                    else:
                        cmd = 'cat '+path+' >> '+short_unpaired_path
                    self.log(console,"command: "+cmd)
                    cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                    cmdProcess.wait()
                    if cmdProcess.returncode != 0:
		        raise ValueError('Error running '+cmd)
                    os.remove(path)
                else:
                    raise ValueError('File '+short_unpaired_library+' missing forward reads file')

        except Exception as e:
            raise ValueError('Unable to download short unpaired reads\n' + str(e))
        return short_unpaired_path
    
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
        provenance[0]['input_ws_objects']=[str(params['short_paired_libraries']),str(params['short_unpaired_libraries']),str(params['long_reads_library']),str(params['min_contig_length']),str(params['num_linear_seqs']),str(params['bridging_mode'])]

        # download, split, and recombine short paired libraries
        download_short_paired(short_paired_libraries)        
        
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
