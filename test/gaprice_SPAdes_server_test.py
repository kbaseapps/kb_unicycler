from __future__ import print_function
import unittest
import os
import time

from os import environ
from ConfigParser import ConfigParser
import psutil

import requests
from biokbase.workspace.client import Workspace as workspaceService  # @UnresolvedImport @IgnorePep8
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService  # @UnresolvedImport @IgnorePep8
from gaprice_SPAdes.gaprice_SPAdesImpl import gaprice_SPAdes


class gaprice_SPAdesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN', None)
        cls.ctx = {'token': cls.token,
                   'provenance': [
                        {'service': 'gaprice_SPAdes',
                         'method': 'please_never_use_it_in_production',
                         'method_params': []
                         }],
                   'authenticated': 1}
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('gaprice_SPAdes'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg['workspace-url']
        cls.shockURL = cls.cfg['shock-url']
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        cls.wsClient = workspaceService(cls.wsURL, token=cls.token)
        cls.serviceImpl = gaprice_SPAdes(cls.cfg)
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        cls.setupTestData()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')
        for node in cls.nodes_to_delete:
            cls.delete_shock_node(node)

        cls.hs.delete_handles(cls.hs.ids_to_handles(cls.handles_to_delete))
        print('Deleted handles ' + str(cls.handles_to_delete))

    @classmethod
    def getWsName(cls):
        if hasattr(cls, 'wsName'):
            print('returning existing workspace name ' + cls.wsName)
            return cls.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_gaprice_SPAdes_" + str(suffix)
        cls.wsClient.create_workspace({'workspace': wsName})
        cls.wsName = wsName
        print('created workspace ' + wsName)
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)

    # Helper script borrowed from the transform service, logger removed
    @classmethod
    def upload_file_to_shock(cls, filePath):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """

        header = dict()
        header["Authorization"] = "Oauth {0}".format(cls.token)

        if filePath is None:
            raise Exception("No file given for upload to SHOCK!")

        with open(os.path.abspath(filePath), 'rb') as dataFile:
            print('POSTing data')
            response = requests.post(cls.shockURL + '/node', headers=header,
                                     data=dataFile, allow_redirects=True)
            print('got response')

        if not response.ok:
            response.raise_for_status()

        result = response.json()

        if result['error']:
            raise Exception(result['error'][0])
        else:
            return result["data"]

    @classmethod
    def upload_file_to_shock_and_get_handle(cls, test_file):
        '''
        Uploads the file in test_file to shock and returns the node and a
        handle to the node.
        '''
        print('loading file to shock: ' + test_file)
        node = cls.upload_file_to_shock(test_file)
        cls.nodes_to_delete.append(node['id'])

        print('creating handle for shock id ' + node['id'])
        handle_id = cls.hs.persist_handle({'id': node['id'],
                                           'type': 'shock',
                                           'url': cls.shockURL
                                           })
        cls.handles_to_delete.append(handle_id)

        md5 = node['file']['checksum']['md5']
        return node['id'], handle_id, md5, node['file']['size']

    @classmethod
    def upload_assembly(cls, key, wsobjname, object_body,
                        fwd_reads, fwd_reads_type,
                        rev_reads, rev_reads_type,
                        kbase_assy=False):
        print('staging data for key ' + key)
        print('uploading forward reads file ' + fwd_reads)
        fwd_id, fwd_handle, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads)

        rev_id = None
        rev_handle = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads)
            rev_id, rev_handle, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads)

        ob = dict(object_body)  # copy
        ob['sequencing_tech'] = 'fake data'
        if not kbase_assy:
            wstype = 'KBaseFile.PairedEndLibrary'
            ob['lib1'] = \
                {'file': {
                          'hid': fwd_handle,
                          'file_name': os.path.split(fwd_reads)[1],
                          'id': fwd_id,
                          'url': cls.shockURL,
                          'type': 'shock',
                          'remote_md5': fwd_md5
                          },
                 'encoding': 'UTF8',
                 'type': fwd_reads_type,
                 'size': fwd_size
                 }
            if rev_reads:
                ob['lib2'] = \
                    {'file': {
                              'hid': rev_handle,
                              'file_name': os.path.split(rev_reads)[1],
                              'id': rev_id,
                              'url': cls.shockURL,
                              'type': 'shock',
                              'remote_md5': rev_md5
                              },
                     'encoding': 'UTF8',
                     'type': rev_reads_type,
                     'size': rev_size
                     }
        else:
            wstype = 'KBaseAssembly.PairedEndLibrary'
            pass  # TODO KBaseAssembly

        print('Saving object data')
        objdata = cls.wsClient.save_objects({
            'workspace': cls.getWsName(),
            'objects': [
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
    def setupTestData(cls):
        print('Shock url ' + cls.shockURL)
        print('WS url ' + cls.wsClient.url)
        print('Handle service url ' + cls.hs.url)
        print('CPUs detected ' + str(psutil.cpu_count()))
        print('Available memory ' + str(psutil.virtual_memory().available))
        print('staging data')
        cls.upload_assembly('frbasic', 'frbasic', {}, 'data/small.forward.fq',
                            'fasta', 'data/small.reverse.fq', 'fasta')
        cls.upload_assembly('intbasic', 'intbasic', {},
                            'data/small.interleaved.fq', None, None, 'fasta')
        print('Data staged.')

    def make_ref(self, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])

    # TODO test KBaseAssy vs. KBFile
    # TODO test single cell vs. normal
    # TODO test separate vs. interlaced
    # TODO test gzip
    # TODO std vs meta vs single cell
    # TODO multiple illumina reads

#     def test_fr_pair(self):
#         ret = self.getImpl().run_SPAdes(
#             self.getContext(),
#             {'workspace_name': self.getWsName(),
#              'read_library_name': self.staged['frbasic']['obj_info'][1],
#              'output_contigset_name': 'frbasic_out'
#              })[0]
#         print(ret)
#         report = self.wsClient.get_objects([{'ref': ret['report_ref']}])
#         print(report)

    def test_interlaced(self):
        key = 'intbasic'
        output_name = 'intbasic_out'
        contigs = [{'description': 'Note MD5 is generated from uppercasing ' +
                                   'the sequence',
                    'name': 'NODE_1_length_64822_cov_8.54567_ID_21',
                    'length': 64822,
                    'id': 'NODE_1_length_64822_cov_8.54567_ID_21',
                    'md5': '8a67351c7d6416039c6f613c31b10764'
                    },
                   {'description': 'Note MD5 is generated from uppercasing ' +
                                   'the sequence',
                    'name': 'NODE_2_length_62607_cov_8.06011_ID_7',
                    'length': 62607,
                    'id': 'NODE_2_length_62607_cov_8.06011_ID_7',
                    'md5': 'e99fade8814bdb861532f493e5deddbd'
                    }]
        source = 'unknown'
        source_id = 'scaffolds.fasta'
        md5 = '09a27dd5107ad23ee2b7695aee8c09d0'
        fasta_md5 = '7f6093a7e56a8dc5cbf1343b166eda67'

        params = {'workspace_name': self.getWsName(),
                  'read_libraries': [self.staged[key]['obj_info'][1]],
                  'output_contigset_name': output_name
                  }

        ret = self.getImpl().run_SPAdes(self.getContext(), params)[0]
        assyref = self.make_ref(self.staged[key]['obj_info'])

        report = self.wsClient.get_objects([{'ref': ret['report_ref']}])[0]
        self.assertEqual('KBaseReport.Report', report['info'][2].split('-')[0])
        self.assertEqual(1, len(report['data']['objects_created']))
        self.assertEqual('Assembled contigs',
                         report['data']['objects_created'][0]['description'])
        self.assertIn('Assembled into ' + str(len(contigs)) + ' contigs',
                      report['data']['text_message'])
        self.assertEqual(1, len(report['provenance']))
        self.assertEqual(1, len(report['provenance'][0]['input_ws_objects']))
        self.assertEqual(
            assyref, report['provenance'][0]['input_ws_objects'][0])
        self.assertEqual(
            1, len(report['provenance'][0]['resolved_ws_objects']))
        self.assertEqual(
            assyref, report['provenance'][0]['resolved_ws_objects'][0])

        cs_ref = report['data']['objects_created'][0]['ref']
        cs = self.wsClient.get_objects([{'ref': cs_ref}])[0]
        self.assertEqual('KBaseGenomes.ContigSet', cs['info'][2].split('-')[0])
        self.assertEqual(1, len(cs['provenance']))
        self.assertEqual(1, len(cs['provenance'][0]['input_ws_objects']))
        self.assertEqual(
            assyref, cs['provenance'][0]['input_ws_objects'][0])
        self.assertEqual(1, len(cs['provenance'][0]['resolved_ws_objects']))
        self.assertEqual(
            assyref, cs['provenance'][0]['resolved_ws_objects'][0])
        self.assertEqual(output_name, cs['info'][1])

        cs_fasta_node = cs['data']['fasta_ref']
        header = {"Authorization": "Oauth {0}".format(self.token)}
        fasta_node = requests.get(self.shockURL + '/node/' + cs_fasta_node,
                                  headers=header, allow_redirects=True).json()
        self.assertEqual(fasta_md5,
                         fasta_node['data']['file']['checksum']['md5'])

        self.assertEqual(output_name, cs['data']['id'])
        self.assertEqual(output_name, cs['data']['name'])
        self.assertEqual(md5, cs['data']['md5'])
        self.assertEqual(source, cs['data']['source'])
        self.assertEqual(source_id, cs['data']['source_id'])

        for i, (exp, got) in enumerate(zip(contigs, cs['data']['contigs'])):
            print('Checking contig ' + str(i) + ': ' + exp['name'])
            exp['s_len'] = exp['length']
            got['s_len'] = len(got['sequence'])
            del got['sequence']
            self.assertDictEqual(exp, got)
