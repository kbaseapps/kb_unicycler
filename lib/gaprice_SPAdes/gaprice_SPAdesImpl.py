#BEGIN_HEADER
# The header block is where all import statments should live
from __future__ import print_function
import os
import sys
import traceback
import uuid
from pprint import pprint, pformat
from biokbase.workspace.client import Workspace as workspaceService
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
    PAIRED_END_TYPE = 'PairedEndLibrary'
    # one of these should be deprecated
    MODULE_NAMES = ['KBaseAssembly', 'KBaseFile'] 
    
    PARAM_IN_WS = 'workspace_name'
    PARAM_IN_LIB = 'read_library_name'
    PARAM_IN_SINGLE_CELL = 'single_cell'
    VERSION = '0.0.1'
    
    THREADS_PER_CORE = 3
    MEMORY_OFFSET = 1000000000 # 1GB
    MIN_MEMORY = 5000000000
    
    URL_WS = 'workspace-url'
    
    workspaceURL = None
    
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
            for chunk in r.iter_content(8192):
                forward_reads_file.write(chunk)
        self.log('done')
        return file_path
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.workspaceURL = config[self.URL_WS]
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

        #### do some basic checks
        objref = ''
        if self.PARAM_IN_WS not in params:
            raise ValueError(self.PARAM_IN_WS + ' parameter is required')
        if self.PARAM_IN_LIB not in params:
            raise ValueError(self.PARAM_IN_LIB + ' parameter is required')
        single_cell = (self.PARAM_IN_SINGLE_CELL in params and
            params[self.PARAM_IN_SINGLE_CELL] == 0)

        #### Get the read library
        ws = workspaceService(self.workspaceURL, token=token)
        objects = ws.get_objects([{'ref': params[self.PARAM_IN_WS] + '/' +
                                   params[self.PARAM_IN_LIB]}])
        data = objects[0]['data']
        info = objects[0]['info']
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
        in_lib_ref = info[6] + '/' + info[0] + '/' + info[4]

        if (module_name not in self.MODULE_NAMES or
            type_name != self.PAIRED_END_TYPE):
            raise ValueError(
                'Only the types ' +
                self.MODULE_NAMES[0] + '.' + self.PAIRED_END_TYPE +
                ' and ' + self.MODULE_NAMES[1] + '.' + self.PAIRED_END_TYPE +
                ' are supported')

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
        
        for_file = shock_download(token, forward_reads)
        rev_file = None
        if (reverse_reads):
            rev_file = shock_download(token, reverse_reads)
            
        
        # construct the SPAdes command
        threads = psutil.cpu_count() * self.THREADS_PER_CORE
        mem = psutil.virtual_memory().available - self.MEMORY_OFFSET
        if mem < self.MIN_MEMORY:
            raise ValueError(
                'Only ' + str(psutil.virtual_memory().available) +
                ' bytes of memory are available. The SPAdes wrapper will ' +
                ' not run without at least ' +
                str(self.MIN_MEMORY + self.MEMORY_OFFSET) + ' bytes available')
        cmd = ['spades.py', '--careful', '--threads', threads, '--memory', mem]
        if single_cell:
            cmd += ['--sc']
        
        
        
        
        #END run_SPAdes

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method run_SPAdes return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
