from __future__ import print_function
import unittest
import os
import json
import time

from os import environ
from ConfigParser import ConfigParser
from pprint import pprint
import psutil

import requests
from requests_toolbelt import MultipartEncoder
from biokbase.workspace.client import Workspace as workspaceService
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService
from gaprice_SPAdes.gaprice_SPAdesImpl import gaprice_SPAdes


class gaprice_SPAdesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        cls.ctx = {'token': token, 'provenance': [{'service': 'gaprice_SPAdes',
            'method': 'please_never_use_it_in_production', 'method_params': []}],
            'authenticated': 1}
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('gaprice_SPAdes'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg['workspace-url']
        cls.shockURL = cls.cfg['shock-url']
        cls.hs = HandleService(url=cls.cfg['handle-service-url'], token=token)
        cls.wsClient = workspaceService(cls.wsURL, token=token)
        cls.serviceImpl = gaprice_SPAdes(cls.cfg)
        cls.staged = {}
        cls.setupTestData(token)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    @classmethod
    def getWsName(cls):
        if hasattr(cls, 'wsName'):
            print('returning existing workspace name ' + cls.wsName)
            return cls.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_gaprice_SPAdes_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': wsName})
        cls.wsName = wsName
        print('created workspace ' + wsName)
        return wsName


    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    # Helper script borrowed from the transform service, logger removed
    @classmethod
    def upload_file_to_shock(cls, filePath, token):
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
#             m = MultipartEncoder(
#                 fields={'upload': (os.path.split(filePath)[-1], dataFile)})
#             header['Content-Type'] = m.content_type
            print('POSTing data')
            response = requests.post(cls.shockURL + '/node', headers = header,
                                     data=dataFile, allow_redirects=True)
#             response = requests.post(
#                 cls.shockURL + "/node", headers=header, data=m,
#                 allow_redirects=True)
            print('got response')

        if not response.ok:
            response.raise_for_status()

        result = response.json()

        if result['error']:
            raise Exception(result['error'][0])
        else:
            return result["data"]

    @classmethod
    def upload_file_to_shock_and_get_handle(cls, test_file, token):
        '''
        Uploads the file in test_file to shock and returns the node and a
        handle to the node.
        '''
        print('loading file to shock: ' + test_file)
        node = cls.upload_file_to_shock(test_file, token)

        print('creating handle for shock id ' + node['id'])
        handle_id = cls.hs.persist_handle({'id': node['id'],
                                           'type': 'shock',
                                           'url': cls.shockURL
                                           })
        md5 = node['file']['checksum']['md5']
        return node['id'], handle_id, md5, node['file']['size']


    @classmethod
    def upload_assembly(cls, key, wsobjname, object_body,
                        fwd_reads, fwd_reads_type,
                        rev_reads, rev_reads_type,
                        token, kbase_assy=False):
        print('staging data for key ' + key)
        print('uploading forward reads file ' + fwd_reads)
        fwd_id, fwd_handle, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads, token)
        
        rev_id = None
        rev_handle = None
        if rev_reads:
            print('uploading forward reads file ' + fwd_reads)
            rev_id, rev_handle, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads, token)

        ob = dict(object_body) # copy
        ob['sequencing_tech'] = 'fake data'
        if not kbase_assy:
            wstype = 'KBaseFile.PairedEndLibrary'
            ob['lib1'] = \
                {'file': {
                          'hid':fwd_handle,
                          'file_name': os.path.split(fwd_reads)[1],
                          'id': fwd_id,
                          'url': cls.shockURL,
                          'type':'shock',
                          'remote_md5': fwd_md5
                          },
                 'encoding':'UTF8',
                 'type':'fastq',
                 'size': rev_size
                 }
            if rev_reads:
                ob['lib2'] = \
                    {'file': {
                              'hid':rev_handle,
                              'file_name': os.path.split(rev_reads)[1],
                              'id': rev_id,
                              'url': cls.shockURL,
                              'type':'shock',
                              'remote_md5': rev_md5
                              },
                     'encoding':'UTF8',
                     'type':'fastq',
                     'size': rev_size
                     }
        else:
            wstype = 'KBaseAssembly.PairedEndLibrary'
            pass # TODO KBaseAssembly
        
        print('Saving object data')
        objdata = cls.wsClient.save_objects({
            'workspace':cls.getWsName(),
            'objects':[
                       {
                        'type': wstype,
                        'data': ob,
                        'name': wsobjname
                        }]
            })[0]
        print('Saved object: ')
        print(objdata)
        ref = str(objdata[6]) + '/' + str(objdata[0]) + '/' + str(objdata[4])
        cls.staged[key] = {'obj_info': objdata,
                           'fwd_node': fwd_id,
                           'rev_node': rev_id,
                           'ref': ref}


    @classmethod
    def setupTestData(cls, token):
        print('Shock url ' + cls.shockURL)
        print('WS url ' + cls.wsClient.url)
        print('Handle service url ' + cls.hs.url)
        print('CPUs detected ' + str(psutil.cpu_count()))
        print('Available memory ' + str(psutil.virtual_memory().available))
        print('staging data')
        cls.upload_assembly('basic', 'basic', {}, 'data/small.forward.fq',
                            'fasta', 'data/small.reverse.fq', 'fasta', token)
        print('Data staged.')
    
    # TODO test KBaseAssy vs. KBFile
    # TODO test single cell vs. normal
    # TODO test separate vs. interlaced
    
    
    def test_basic_ops(self):
        print('running test_basic_ops')
        ret = self.getImpl().run_SPAdes(
            self.getContext(),
            {'workspace_name': self.getWsName(),
             'read_library_name': self.staged['basic']['obj_info'][1],
             'output_contigset_name': 'basic_out'
             })
        print(ret)
