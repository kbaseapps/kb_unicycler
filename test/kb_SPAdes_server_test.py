from __future__ import print_function
import unittest
import os
import time

from os import environ
from ConfigParser import ConfigParser
import psutil

import requests
from biokbase.workspace.client import Workspace as workspaceService  # @UnresolvedImport @IgnorePep8
from biokbase.workspace.client import ServerError as WorkspaceError  # @UnresolvedImport @IgnorePep8
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService  # @UnresolvedImport @IgnorePep8
from kb_SPAdes.kb_SPAdesImpl import kb_SPAdes
from ReadsUtils.baseclient import ServerError
from ReadsUtils.ReadsUtilsClient import ReadsUtils
from kb_SPAdes.kb_SPAdesServer import MethodContext
from pprint import pprint
import shutil
import inspect
from kb_SPAdes.GenericClient import GenericClient


class gaprice_SPAdesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = environ.get('KB_AUTH_TOKEN')
        cls.callbackURL = environ.get('SDK_CALLBACK_URL')
        print('CB URL: ' + cls.callbackURL)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': cls.token,
                        'provenance': [
                            {'service': 'kb_SPAdes',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_SPAdes'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg['workspace-url']
        cls.shockURL = cls.cfg['shock-url']
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        cls.wsClient = workspaceService(cls.wsURL, token=cls.token)
        wssuffix = int(time.time() * 1000)
        wsName = "test_kb_SPAdes_" + str(wssuffix)
        cls.wsinfo = cls.wsClient.create_workspace({'workspace': wsName})
        print('created workspace ' + cls.getWsName())
        cls.serviceImpl = kb_SPAdes(cls.cfg)
        cls.readUtilsImpl = ReadsUtils(cls.callbackURL, token=cls.token)
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        cls.setupTestData()
        print('\n\n=============== Starting tests ==================')

    @classmethod
    def tearDownClass(cls):

        print('\n\n=============== Cleaning up ==================')

        if hasattr(cls, 'wsinfo'):
            cls.wsClient.delete_workspace({'workspace': cls.getWsName()})
            print('Test workspace was deleted: ' + cls.getWsName())
        if hasattr(cls, 'nodes_to_delete'):
            for node in cls.nodes_to_delete:
                cls.delete_shock_node(node)
        if hasattr(cls, 'handles_to_delete'):
            cls.hs.delete_handles(cls.hs.ids_to_handles(cls.handles_to_delete))
            print('Deleted handles ' + str(cls.handles_to_delete))

    @classmethod
    def getWsName(cls):
        return cls.wsinfo[1]

    def getImpl(self):
        return self.serviceImpl

    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.token)}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)

    # Helper script borrowed from the transform service, logger removed
    @classmethod
    def upload_file_to_shock(cls, file_path):
        """
        Use HTTP multi-part POST to save a file to a SHOCK instance.
        """

        header = dict()
        header["Authorization"] = "Oauth {0}".format(cls.token)

        if file_path is None:
            raise Exception("No file given for upload to SHOCK!")

        with open(os.path.abspath(file_path), 'rb') as dataFile:
            files = {'upload': dataFile}
            print('POSTing data')
            response = requests.post(
                cls.shockURL + '/node', headers=header, files=files,
                stream=True, allow_redirects=True)
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
        pprint(node)
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
    def upload_reads(cls, wsobjname, object_body, fwd_reads,
                     rev_reads=None, single_end=False, sequencing_tech='Illumina',
                     single_genome='1'):

        ob = dict(object_body)  # copy
        ob['sequencing_tech'] = sequencing_tech
#        ob['single_genome'] = single_genome
        ob['wsname'] = cls.getWsName()
        ob['name'] = wsobjname
        if single_end or rev_reads:
            ob['interleaved']= 0
        else:
            ob['interleaved']= 1
        print('\n===============staging data for object ' + wsobjname +
              '================')
        print('uploading forward reads file ' + fwd_reads['file'])
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads['file'])

        ob['fwd_id']= fwd_id
        rev_id = None
        rev_handle_id = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads['file'])
            rev_id, rev_handle_id, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads['file'])
            ob['rev_id']= rev_id
        obj_ref = cls.readUtilsImpl.upload_reads(ob)
        objdata = cls.wsClient.get_object_info_new({
            'objects': [{'ref': obj_ref['obj_ref']}]
            })[0]
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 'fwd_node_id': fwd_id,
                                 'rev_node_id': rev_id,
                                 'fwd_handle_id': fwd_handle_id,
                                 'rev_handle_id': rev_handle_id
                                 }

    @classmethod
    def upload_assembly(cls, wsobjname, object_body, fwd_reads,
                        rev_reads=None, kbase_assy=False,
                        single_end=False, sequencing_tech='Illumina'):
        if single_end and rev_reads:
            raise ValueError('u r supr dum')

        print('\n===============staging data for object ' + wsobjname +
              '================')
        print('uploading forward reads file ' + fwd_reads['file'])
        fwd_id, fwd_handle_id, fwd_md5, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads['file'])
        fwd_handle = {
                      'hid': fwd_handle_id,
                      'file_name': fwd_reads['name'],
                      'id': fwd_id,
                      'url': cls.shockURL,
                      'type': 'shock',
                      'remote_md5': fwd_md5
                      }

        ob = dict(object_body)  # copy
        ob['sequencing_tech'] = sequencing_tech
        if kbase_assy:
            if single_end:
                wstype = 'KBaseAssembly.SingleEndLibrary'
                ob['handle'] = fwd_handle
            else:
                wstype = 'KBaseAssembly.PairedEndLibrary'
                ob['handle_1'] = fwd_handle
        else:
            if single_end:
                wstype = 'KBaseFile.SingleEndLibrary'
                obkey = 'lib'
            else:
                wstype = 'KBaseFile.PairedEndLibrary'
                obkey = 'lib1'
            ob[obkey] = \
                {'file': fwd_handle,
                 'encoding': 'UTF8',
                 'type': fwd_reads['type'],
                 'size': fwd_size
                 }

        rev_id = None
        rev_handle_id = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads['file'])
            rev_id, rev_handle_id, rev_md5, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads['file'])
            rev_handle = {
                          'hid': rev_handle_id,
                          'file_name': rev_reads['name'],
                          'id': rev_id,
                          'url': cls.shockURL,
                          'type': 'shock',
                          'remote_md5': rev_md5
                          }
            if kbase_assy:
                ob['handle_2'] = rev_handle
            else:
                ob['lib2'] = \
                    {'file': rev_handle,
                     'encoding': 'UTF8',
                     'type': rev_reads['type'],
                     'size': rev_size
                     }

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
        print('Saved object objdata: ')
        pprint(objdata)
        print('Saved object ob: ')
        pprint(ob)
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 'fwd_node_id': fwd_id,
                                 'rev_node_id': rev_id,
                                 'fwd_handle_id': fwd_handle_id,
                                 'rev_handle_id': rev_handle_id
                                 }

    @classmethod
    def upload_empty_data(cls, wsobjname):
        objdata = cls.wsClient.save_objects({
            'workspace': cls.getWsName(),
            'objects': [{'type': 'Empty.AType',
                         'data': {},
                         'name': 'empty'
                         }]
            })[0]
        cls.staged[wsobjname] = {'info': objdata,
                                 'ref': cls.make_ref(objdata),
                                 }

    @classmethod
    def setupTestData(cls):
        print('Shock url ' + cls.shockURL)
        print('WS url ' + cls.wsClient.url)
        print('Handle service url ' + cls.hs.url)
        print('CPUs detected ' + str(psutil.cpu_count()))
        print('Available memory ' + str(psutil.virtual_memory().available))
        print('staging data')

        # get file type from type
        fwd_reads = {'file': 'data/small.forward.fq',
                     'name': 'test_fwd.fastq',
                     'type': 'fastq'}
        # get file type from handle file name
        rev_reads = {'file': 'data/small.reverse.fq',
                     'name': 'test_rev.FQ',
                     'type': ''}
        # get file type from shock node file name
        int_reads = {'file': 'data/interleaved.fq',
                     'name': '',
                     'type': ''}
        int64_reads = {'file': 'data/interleaved64.fq',
                       'name': '',
                       'type': ''}
        pacbio_reads = {'file': 'data/pacbio_filtered_small.fastq.gz',
                        'name': '',
                        'type': ''}
        pacbio_ccs_reads = {'file': 'data/pacbioCCS_small.fastq.gz',
                            'name': '',
                            'type': ''}
        iontorrent_reads = {'file': 'data/IonTorrent_single.fastq.gz',
                            'name': '',
                            'type': ''}
        plasmid1_reads = {'file': 'data/pl1.fq.gz',
                          'name': '',
                          'type': ''}
        plasmid2_reads = {'file': 'data/pl2.fq.gz',
                          'name': '',
                          'type': ''}
        cls.upload_reads('frbasic', {}, fwd_reads, rev_reads=rev_reads)
        cls.upload_reads('intbasic', {'single_genome': 1}, int_reads)
        cls.upload_reads('intbasic64', {'single_genome': 1}, int64_reads)
        cls.upload_reads('pacbio', {'single_genome': 1},
                            pacbio_reads, single_end=True, sequencing_tech="PacBio CLR")
        cls.upload_reads('pacbioccs', {'single_genome': 1},
                            pacbio_ccs_reads, single_end=True, sequencing_tech="PacBio CCS")
        cls.upload_reads('iontorrent', {'single_genome': 1},
                            iontorrent_reads, single_end=True, sequencing_tech="IonTorrent")
        cls.upload_reads('meta', {'single_genome': 0}, fwd_reads,
                            rev_reads=rev_reads)
        cls.upload_reads('meta2', {'single_genome': 0}, fwd_reads,
                            rev_reads=rev_reads)
        cls.upload_reads('meta_single_end', {'single_genome': 0}, fwd_reads, single_end=True)
        cls.upload_reads('reads_out', {'read_orientation_outward': 1},
                            int_reads)
        cls.upload_assembly('frbasic_kbassy', {}, fwd_reads,
                            rev_reads=rev_reads, kbase_assy=True)
        cls.upload_assembly('intbasic_kbassy', {}, int_reads, kbase_assy=True)
        cls.upload_reads('single_end', {}, fwd_reads, single_end=True)
        cls.upload_reads('single_end2', {}, rev_reads, single_end=True)
        cls.upload_reads('plasmid_reads', {'single_genome': 1},
                         plasmid1_reads, rev_reads=plasmid2_reads)
        shutil.copy2('data/small.forward.fq', 'data/small.forward.bad')
        bad_fn_reads = {'file': 'data/small.forward.bad',
                        'name': '',
                        'type': ''}
        cls.upload_assembly('bad_shk_name', {}, bad_fn_reads)
        bad_fn_reads['file'] = 'data/small.forward.fq'
        bad_fn_reads['name'] = 'file.terrible'
        cls.upload_assembly('bad_file_name', {}, bad_fn_reads)
        bad_fn_reads['name'] = 'small.forward.fastq'
        bad_fn_reads['type'] = 'xls'
        cls.upload_assembly('bad_file_type', {}, bad_fn_reads)
        cls.upload_assembly('bad_node', {}, fwd_reads)
        cls.delete_shock_node(cls.nodes_to_delete.pop())
        cls.upload_empty_data('empty')
        print('Data staged.')

    @classmethod
    def make_ref(self, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])

    def test_fr_pair_kbfile(self):

        self.run_success(
            ['frbasic'], 'frbasic_out',
            {'contigs':
             [{'name': 'NODE_1_length_64822_cov_8.99582',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_8.99582',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               },
              {'name': 'NODE_2_length_62656_cov_8.64322',
               'length': 62656,
               'id': 'NODE_2_length_62656_cov_8.64322',
               'md5': '8e7483c2223234aeff0c78f70b2e068a'
               }],
             'md5': '08d0b92ce7c0a5e346b3077436edaa42',
             'fasta_md5': '03a8b6fc00638dd176998e25e4a208b6'
             })

    def test_fr_pair_kbassy(self):

        self.run_success(
            ['frbasic_kbassy'], 'frbasic_kbassy_out',
            {'contigs':
             [{'name': 'NODE_1_length_64822_cov_8.99582',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_8.99582',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               },
              {'name': 'NODE_2_length_62656_cov_8.64322',
               'length': 62656,
               'id': 'NODE_2_length_62656_cov_8.64322',
               'md5': '8e7483c2223234aeff0c78f70b2e068a'
               }],
             'md5': '08d0b92ce7c0a5e346b3077436edaa42',
             'fasta_md5': '03a8b6fc00638dd176998e25e4a208b6'
             })

    def test_interlaced_kbfile(self):

        self.run_success(
            ['intbasic'], 'intbasic_out',
            {'contigs':
             [{'name': 'NODE_1_length_4084_cov_1.3132',
               'length': 4084,
               'id': 'NODE_1_length_4084_cov_1.3132',
               'md5': '8d434467d0158fd0eaa2e909c7314a69'
               },
              {'name': 'NODE_2_length_3873_cov_2.43151',
               'length': 3873,
               'id': 'NODE_2_length_3873_cov_2.43151',
               'md5': '64668c2d1ccb121a88404989b54808c7'
               }],
             'md5': '200c2a4b6bc9f79fbf2fecdbcf997978',
             'fasta_md5': 'ab7aadf4046d5fdabd71ae5813b34f7f'
             }, contig_count=1450)

    def test_metagenome_kbfile(self):
        self.run_success(
            ['meta'], 'metabasic_out',
            {'contigs':
             [{'name': 'NODE_1_length_64822_cov_8.99795',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_8.99795',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               },
              {'name': 'NODE_2_length_62656_cov_8.64555',
               'length': 62656,
               'id': 'NODE_2_length_62656_cov_8.64555',
               'md5': '8e7483c2223234aeff0c78f70b2e068a'
               }],
             'md5': '08d0b92ce7c0a5e346b3077436edaa42',
             'fasta_md5': 'ca42754da16f76159db91ef986f4d276'
             }, contig_count=2, dna_source='metagenomic')

    def test_metagenome_multiple(self):
        self.run_error(['meta', 'meta2'],
                       'Metagenome assembly requires that one ' +
                       'and only one paired end library as input. ' +
                       '2 libraries detected.',
                       dna_source='metagenomic')

    def test_metagenome_single_end(self):
        self.run_error(['meta_single_end'],
                       'Metagenome assembly requires that one ' +
                       'and only one paired end library as input.',
                       dna_source='metagenomic')

    def test_plasmid_kbfile(self):
        self.run_success(
            ['plasmid_reads'], 'plasmid_out',
            {'contigs':
             [{'name': 'NODE_1_length_9667_cov_9.19777_component_0',
               'length': 9667,
               'id': 'NODE_1_length_9667_cov_9.19777_component_0',
               'md5': 'c8c02dd26a71aa6ef5486802f070aa0d'
               }],
             'md5': '010787c609153b4c07103f54051a2761',
             'fasta_md5': 'dd55c47f1c16657762222d0152683bc9'
             }, contig_count=1, dna_source='plasmid')

    def test_plasmid_multiple(self):
        self.run_error(['plasmid_reads', 'frbasic'],
                       'Plasmid assembly requires that one ' +
                       'and only one library as input. ' +
                       '2 libraries detected.',
                       dna_source='plasmid')

    def test_interlaced_kbassy(self):

        self.run_success(
            ['intbasic_kbassy'], 'intbasic_kbassy_out',
            {'contigs':
             [{'name': 'NODE_1_length_4084_cov_1.3132',
               'length': 4084,
               'id': 'NODE_1_length_4084_cov_1.3132',
               'md5': '8d434467d0158fd0eaa2e909c7314a69'
               },
              {'name': 'NODE_2_length_3873_cov_2.43151',
               'length': 3873,
               'id': 'NODE_2_length_3873_cov_2.43151',
               'md5': '64668c2d1ccb121a88404989b54808c7'
               }],
             'md5': '200c2a4b6bc9f79fbf2fecdbcf997978',
             'fasta_md5': 'ab7aadf4046d5fdabd71ae5813b34f7f'
             }, contig_count=1450, dna_source='')

    def test_multiple(self):
        self.run_success(
            ['intbasic_kbassy', 'frbasic'], 'multiple_out',
            {'contigs':
             [{'name': 'NODE_1_length_64822_cov_4.59581',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_4.59581',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               },
              {'name': 'NODE_2_length_62656_cov_4.41539',
               'length': 62656,
               'id': 'NODE_2_length_62656_cov_4.41539',
               'md5': '8e7483c2223234aeff0c78f70b2e068a'
               }],
             'md5': '43db43d141d5f122b93cec5718eead70',
             'fasta_md5': '0e2de918428b3bb8e6ed42669428b868'
             }, contig_count=1452, dna_source='None')

    def test_multiple_pacbio_illumina(self):
        self.run_success(
            ['intbasic_kbassy', 'pacbio'], 'pacbio_multiple_out',
            {'contigs':
             [{'name': 'NODE_1_length_4084_cov_1.3132',
               'length': 4084,
               'id': 'NODE_1_length_4084_cov_1.3132',
               'md5': '8d434467d0158fd0eaa2e909c7314a69'
               },
              {'name': 'NODE_2_length_3873_cov_2.43151',
               'length': 3873,
               'id': 'NODE_2_length_3873_cov_2.43151',
               'md5': '64668c2d1ccb121a88404989b54808c7'
               }],
             'md5': '38c94314d0db51075a78ab8d5b85cb60',
             'fasta_md5': '6a23b8a37c33f1bd63de77d5a67f2d0c'
             }, contig_count=1447, dna_source='None')

    def test_multiple_pacbio_single(self):
        self.run_success(
            ['single_end', 'pacbio'], 'pacbio_single_out',
            {'contigs':
             [{'name': 'NODE_1_length_46307_cov_4.43576',
               'length': 46307,
               'id': 'NODE_1_length_46307_cov_4.43576',
               'md5': 'fe4d97654a63c0f2f172894ae7b3ad85'
               },
              {'name': 'NODE_2_length_41003_cov_4.30011',
               'length': 41003,
               'id': 'NODE_2_length_41003_cov_4.30011',
               'md5': 'a3bb8457f8e98f95d471d4d43653c2dd'
               }],
             'md5': 'cade3c3a5db42701e09c3f091edd83e6',
             'fasta_md5': 'ad834a03295f11ab0b10308c72a89626'
             }, contig_count=7, dna_source='None')

    def test_multiple_single(self):
        self.run_success(
            ['single_end', 'single_end2'], 'multiple_single_out',
            {'contigs':
             [{'name': 'NODE_2_length_62656_cov_8.64322',
               'length': 62656,
               'id': 'NODE_2_length_62656_cov_8.64322',
               'md5': '8e7483c2223234aeff0c78f70b2e068a'
               },
              {'name': 'NODE_1_length_64822_cov_8.99582',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_8.99582',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               }],
             'md5': '08d0b92ce7c0a5e346b3077436edaa42',
             'fasta_md5': '03a8b6fc00638dd176998e25e4a208b6'
             }, contig_count=2, dna_source='None')

    def test_multi_paired_single(self):
        self.run_success(
            ['intbasic_kbassy','single_end'], 'multi_paired_single_out',
            {'contigs':
             [{'name': 'NODE_274_length_495_cov_1.22249',
               'length': 495,
               'id': 'NODE_274_length_495_cov_1.22249',
               'md5': 'c393d68ecaf4cb1c4644d21960c6b72b'
               },
              {'name': 'NODE_49_length_928_cov_2.0517',
               'length': 928,
               'id': 'NODE_49_length_928_cov_2.0517',
               'md5': 'fe82bda17020c4ac02081245ca9d3fab'
               }],
             'md5': '5787862150f820a2629bcddb3b2df8f8',
             'fasta_md5': '5231eedcd0d2ea5087b4d9594f40e443'
             }, contig_count=1461, dna_source='None')

    def test_iontorrent_alone(self):
        self.run_non_deterministic_success(
            ['iontorrent'], 'iontorrent_alone_out',
            dna_source='None')

    def test_multiple_iontorrent_illumina(self):
        self.run_error(['intbasic_kbassy', 'iontorrent'],
                       'Both IonTorrent and Illumina read libraries exist. SPAdes ' +
                       'can not assemble them together.')

    def test_pacbio_alone(self):
        self.run_error(['pacbio'],
                       'Per SPAdes requirements : If doing PacBio CLR reads, you must also ' +
                       'supply at least one paired end or single end reads library')

    def test_pacbioccs_alone(self):
        self.run_success(
            ['pacbioccs'], 'pacbioccs_alone_out',
            {'contigs':
             [{'name': 'NODE_1_length_497242_cov_3.07893',
               'length': 497242,
               'id': 'NODE_1_length_497242_cov_3.07893',
               'md5': '3bce716f534a547da4c42e60c81a9e1b'
               },
              {'name': 'NODE_2_length_421917_cov_3.16403',
               'length': 421917,
               'id': 'NODE_2_length_421917_cov_3.16403',
               'md5': '0d5ff1244c38dc7e1b6e912b6bd7114e'
               }],
             'md5': '3a2bcdd1dd5795e038160f227b5627df',
             'fasta_md5': 'eff807bfdc3fdc5b0343c35138bdf74f'
             }, contig_count=88, dna_source='None')

    def test_multiple_pacbioccs_illumina(self):
        self.run_success(
            ['intbasic_kbassy', 'pacbioccs'], 'pacbioccs_multiple_out',
            {'contigs':
             [{'name': 'NODE_1_length_752414_cov_3.12176',
               'length': 752414,
               'id': 'NODE_1_length_752414_cov_3.12176',
               'md5': '950378bba6923ea17b7fd33ed124dea0'
               },
              {'name': 'NODE_2_length_459413_cov_3.19014',
               'length': 459413,
               'id': 'NODE_2_length_459413_cov_3.19014',
               'md5': '389c3acf2586f42e9c2c9bf5fe5fba12'
               }],
             'md5': '2bd209a0b2851362cb2fda75a500c90e',
             'fasta_md5': '8bfd5da65e11d068672201d4f857e4dd'
             }, contig_count=76, dna_source='None')

    def test_single_reads(self):
        self.run_success(
            ['single_end'], 'single_out',
            {'contigs':
             [{'name': 'NODE_1_length_46307_cov_4.43576',
               'length': 46307,
               'id': 'NODE_1_length_46307_cov_4.43576',
               'md5': 'fe4d97654a63c0f2f172894ae7b3ad85'
               },
              {'name': 'NODE_2_length_41003_cov_4.30011',
               'length': 41003,
               'id': 'NODE_2_length_41003_cov_4.30011',
               'md5': 'a3bb8457f8e98f95d471d4d43653c2dd'
               }],
             'md5': 'cade3c3a5db42701e09c3f091edd83e6',
             'fasta_md5': 'ad834a03295f11ab0b10308c72a89626'
             }, contig_count=7, dna_source='None')


    def test_multiple_bad(self):
        # Testing where input reads have different phred types (33 and 64)
        self.run_error(['intbasic64', 'frbasic'],
                       ('The set of Reads objects passed in have reads that have different phred ' +
                        'type scores. SPAdes does not support assemblies of reads with different ' +
                        'phred type scores.\nThe following read objects have ' +
                        'phred 33 scores : {}/frbasic.\n' +
                        'The following read objects have phred 64 scores : ' +
                        '{}/intbasic64').format(self.getWsName(), self.getWsName()),
                       exception=ValueError)
    
    def test_single_cell(self):

        self.run_success(
            ['frbasic'], 'single_cell_out',
            {'contigs':
             [{'name': 'NODE_1_length_64822_cov_8.99582',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_8.99582',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               },
              {'name': 'NODE_2_length_62656_cov_8.64322',
               'length': 62656,
               'id': 'NODE_2_length_62656_cov_8.64322',
               'md5': '8e7483c2223234aeff0c78f70b2e068a'
               }],
             'md5': '08d0b92ce7c0a5e346b3077436edaa42',
             'fasta_md5': '03a8b6fc00638dd176998e25e4a208b6'
             }, dna_source='single_cell')

    def test_metagenome(self):

        self.run_success(
            ['meta'], 'metagenome_out',
            {'contigs':
             [{'name': 'NODE_1_length_64822_cov_8.99795',
               'length': 64822,
               'id': 'NODE_1_length_64822_cov_8.99795',
               'md5': '8a67351c7d6416039c6f613c31b10764'
               }],
             'md5': '7bebd932338eca9331921dc605791aea',
             'fasta_md5': '8da1994279e071c9dd2b2cef57c7f092'
             }, min_contig_length=63000, dna_source='metagenomic')

    def test_invalid_min_contig_length(self):

        self.run_error(
            ['foo'], 'min_contig_length must be of type int', wsname='fake', min_contig_length='not an int!')
    
    def test_no_workspace_param(self):

        self.run_error(
            ['foo'], 'workspace_name parameter is required', wsname=None)

    def test_bad_workspace_name(self):

        self.run_error(['foo'], 'Invalid workspace name bad|name',
                       wsname='bad|name')

    def test_non_extant_workspace(self):

        self.run_error(
            ['foo'], 'Object foo cannot be accessed: No workspace with name ' +
            'Ireallyhopethisworkspacedoesntexistorthistestwillfail exists',
            wsname='Ireallyhopethisworkspacedoesntexistorthistestwillfail',
            exception=WorkspaceError)

    # TEST REMOVED SINCE FROM THE UI IT IS A REFERENCE (Old logic in Impl broke UI)
    # def test_bad_lib_name(self):

    #   self.run_error(['bad&name'], 'Invalid workspace object name bad&name')

    def test_no_libs_param(self):

        self.run_error(None, 'read_libraries parameter is required')

    def test_no_libs_list(self):

        self.run_error('foo', 'read_libraries must be a list')

    def test_non_extant_lib(self):

        self.run_error(
            ['foo'],
            ('No object with name foo exists in workspace {} ' +
             '(name {})').format(str(self.wsinfo[0]), self.wsinfo[1]),
            exception=WorkspaceError)

    def test_no_libs(self):

        self.run_error([], 'At least one reads library must be provided')

    def test_no_output_param(self):

        self.run_error(
            ['foo'], 'output_contigset_name parameter is required',
            output_name=None)

    def test_no_output_name(self):

        self.run_error(
            ['foo'], 'output_contigset_name parameter is required',
            output_name='')

    def test_bad_output_name(self):

        self.run_error(
            ['frbasic'], 'Invalid workspace object name bad*name',
            output_name='bad*name')

    def test_inconsistent_metagenomics_1(self):

        self.run_error(
            ['intbasic'],
            'Reads object ' + self.getWsName() + '/intbasic (' +
            self.staged['intbasic']['ref'] +
            ') is marked as containing dna from a single genome but the ' +
            'assembly method was specified as metagenomic',
            dna_source='metagenomic')

    def test_inconsistent_metagenomics_2(self):

        self.run_error(
            ['meta'],
            'Reads object ' + self.getWsName() + '/meta (' +
            self.staged['meta']['ref'] +
            ') is marked as containing metagenomic data but the assembly ' +
            'method was not specified as metagenomic')

    def test_outward_reads(self):

        self.run_error(
            ['reads_out'],
            'Reads object ' + self.getWsName() + '/reads_out (' +
            self.staged['reads_out']['ref'] +
            ') is marked as having outward oriented reads, which SPAdes ' +
            'does not support.')

    def test_bad_module(self):

        self.run_error(['empty'],
                       'Invalid type for object ' +
                       self.staged['empty']['ref'] + ' (empty). Only the ' +
                       'types KBaseAssembly.PairedEndLibrary and ' +
                       'KBaseFile.PairedEndLibrary are supported')

    def test_bad_shock_filename(self):

        self.run_error(
            ['bad_shk_name'],
            ('Shock file name is illegal: small.forward.bad. Expected FASTQ ' +
             'file. Reads object bad_shk_name ({}). Shock node ' +
             '{}').format(self.staged['bad_shk_name']['ref'],
                          self.staged['bad_shk_name']['fwd_node_id']),
            exception=ServerError)

    def test_bad_handle_filename(self):

        self.run_error(
            ['bad_file_name'],
            ('Handle file name from reads Workspace object is illegal: file.terrible. ' +
             'Expected FASTQ file. Reads object bad_file_name ({}). Shock node ' +
             '{}').format(self.staged['bad_file_name']['ref'],
                          self.staged['bad_file_name']['fwd_node_id']),
            exception=ServerError)

    def test_bad_file_type(self):

        self.run_error(
            ['bad_file_type'],
            ('File type from reads Workspace object is illegal: .xls. Expected ' +
             'FASTQ file. Reads object bad_file_type ({}). Shock node ' +
             '{}').format(self.staged['bad_file_type']['ref'],
                          self.staged['bad_file_type']['fwd_node_id']),
            exception=ServerError)

    def test_bad_shock_node(self):

        self.run_error(['bad_node'],
                       ('Handle error for object {}: The Handle Manager ' +
                        'reported a problem while attempting to set Handle ACLs: ' +
                        'Unable to set acl(s) on handles ' +
                        '{}').format(
                            self.staged['bad_node']['ref'],
                            self.staged['bad_node']['fwd_handle_id']),
                       exception=ServerError)

    def test_provenance(self):

        frbasic = 'frbasic'
        ref = self.make_ref(self.staged[frbasic]['info'])
        gc = GenericClient(self.callbackURL, use_url_lookup=False)
        gc.sync_call('CallbackServer.set_provenance',
                     [{'service': 'myserv',
                       'method': 'mymeth',
                       'service_ver': '0.0.2',
                       'method_params': ['foo', 'bar', 'baz'],
                       'input_ws_objects': [ref]
                       }]
                     )

        params = {'workspace_name': self.getWsName(),
                  'read_libraries': [frbasic],
                  'output_contigset_name': 'foo'
                  }

        ret = self.getImpl().run_SPAdes(self.ctx, params)[0]
        report = self.wsClient.get_objects([{'ref': ret['report_ref']}])[0]
        assembly_ref = report['data']['objects_created'][0]['ref']
        assembly = self.wsClient.get_objects([{'ref': assembly_ref}])[0]

        rep_prov = report['provenance']
        assembly_prov = assembly['provenance']
        self.assertEqual(len(rep_prov), 1)
        self.assertEqual(len(assembly_prov), 2)
#       rep_prov = rep_prov[0]
#       assembly_prov = assembly_prov[0]
#       for p in [rep_prov, assembly_prov]:
#            self.assertEqual(p['service'], 'myserv')
#            self.assertEqual(p['method'], 'mymeth')
#            self.assertEqual(p['service_ver'], '0.0.2')
#            self.assertEqual(p['method_params'], ['foo', 'bar', 'baz'])
#            self.assertEqual(p['input_ws_objects'], [ref])
#            sa = p['subactions']
#            self.assertEqual(len(sa), 1)
#            sa = sa[0]
#            self.assertEqual(
#                sa['name'],
#                'kb_read_library_to_file')
#            self.assertEqual(
#                sa['code_url'],
#                'https://github.com/MrCreosote/kb_read_library_to_file')
# don't check ver or commit since they can change from run to run

    def run_error(self, readnames, error, wsname=('fake'), output_name='out',
                  dna_source=None, min_contig_len=0, exception=ValueError):

        test_name = inspect.stack()[1][3]
        print('\n***** starting expected fail test: ' + test_name + ' *****')
        print('    libs: ' + str(readnames))

        if wsname == ('fake'):
            wsname = self.getWsName()

        params = {}
        if (wsname is not None):
            if wsname == 'None':
                params['workspace_name'] = None
            else:
                params['workspace_name'] = wsname

        if (readnames is not None):
            params['read_libraries'] = readnames

        if (output_name is not None):
            params['output_contigset_name'] = output_name

        if not (dna_source is None):
            params['dna_source'] = dna_source

        params['min_contig_len'] = min_contig_len

        with self.assertRaises(exception) as context:
            self.getImpl().run_SPAdes(self.ctx, params)
        self.assertEqual(error, str(context.exception.message))

    def run_success(self, readnames, output_name, expected, contig_count=None,
                    min_contig_length=0, dna_source=None):

        test_name = inspect.stack()[1][3]
        print('\n**** starting expected success test: ' + test_name + ' *****')
        print('   libs: ' + str(readnames))

        if not contig_count:
            contig_count = len(expected['contigs'])

        print("READNAMES: " + str(readnames))
        print("STAGED: " + str(self.staged))

        libs = [self.staged[n]['info'][1] for n in readnames]
#        assyrefs = sorted(
#            [self.make_ref(self.staged[n]['info']) for n in readnames])

        params = {'workspace_name': self.getWsName(),
                  'read_libraries': libs,
                  'output_contigset_name': output_name,
                  'min_contig_length': min_contig_length
                  }

        if not (dna_source is None):
            if dna_source == 'None':
                params['dna_source'] = None
            else:
                params['dna_source'] = dna_source

        ret = self.getImpl().run_SPAdes(self.ctx, params)[0]

        report = self.wsClient.get_objects([{'ref': ret['report_ref']}])[0]
        self.assertEqual('KBaseReport.Report', report['info'][2].split('-')[0])
        self.assertEqual(1, len(report['data']['objects_created']))
        self.assertEqual('Assembled contigs',
                         report['data']['objects_created'][0]['description'])
        self.assertIn('Assembled into ' + str(contig_count) +
                      ' contigs', report['data']['text_message'])
        print("PROVENANCE: " + str(report['provenance']))
        self.assertEqual(1, len(report['provenance']))
        # PERHAPS ADD THESE TESTS BACK IN THE FUTURE, BUT AssemblyUtils and this
        # would need to pass in the extra provenance information
#        self.assertEqual(
#            assyrefs, sorted(report['provenance'][0]['input_ws_objects']))
#        self.assertEqual(
#            assyrefs,
#            sorted(report['provenance'][0]['resolved_ws_objects']))

        assembly_ref = report['data']['objects_created'][0]['ref']
        assembly = self.wsClient.get_objects([{'ref': assembly_ref}])[0]
        # print("ASSEMBLY OBJECT:")
        self.assertEqual('KBaseGenomeAnnotations.Assembly', assembly['info'][2].split('-')[0])
        self.assertEqual(1, len(assembly['provenance']))
        # PERHAPS ADD THESE TESTS BACK IN THE FUTURE, BUT AssemblyUtils and this
        # would need to pass in the extra provenance information
#        self.assertEqual(
#            assyrefs, sorted(assembly['provenance'][0]['input_ws_objects']))
#        self.assertEqual(
#            assyrefs, sorted(assembly['provenance'][0]['resolved_ws_objects']))
        self.assertEqual(output_name, assembly['info'][1])

#        handle_id = assembly['data']['fasta_handle_ref']
#        print("HANDLE ID:" + handle_id)
#        handle_ids_list = list()
#        handle_ids_list.append(handle_id)
#        print("HANDLE IDS:" + str(handle_ids_list))
#        temp_handle_info = self.hs.hids_to_handles(handle_ids_list)
        temp_handle_info = self.hs.hids_to_handles([assembly['data']['fasta_handle_ref']])
        print("HANDLE OBJECT:")
        pprint(temp_handle_info)
        assembly_fasta_node = temp_handle_info[0]['id']
        self.nodes_to_delete.append(assembly_fasta_node)
        header = {"Authorization": "Oauth {0}".format(self.token)}
        fasta_node = requests.get(self.shockURL + '/node/' + assembly_fasta_node,
                                  headers=header, allow_redirects=True).json()
        self.assertEqual(expected['fasta_md5'],
                         fasta_node['data']['file']['checksum']['md5'])

        self.assertEqual(contig_count, len(assembly['data']['contigs']))
        self.assertEqual(output_name, assembly['data']['assembly_id'])
        # self.assertEqual(output_name, assembly['data']['name']) #name key doesnt seem to exist
        self.assertEqual(expected['md5'], assembly['data']['md5'])

        for exp_contig in expected['contigs']:
            if exp_contig['id'] in assembly['data']['contigs']:
                obj_contig = assembly['data']['contigs'][exp_contig['id']]
                self.assertEqual(exp_contig['name'], obj_contig['name'])
                self.assertEqual(exp_contig['md5'], obj_contig['md5'])
                self.assertEqual(exp_contig['length'], obj_contig['length'])
            else:
                # Hacky way to do this, but need to see all the contig_ids
                # They changed because the SPAdes version changed and
                # Need to see them to update the tests accordingly.
                # If code gets here this test is designed to always fail, but show results.
                self.assertEqual(str(assembly['data']['contigs']),"BLAH")


    def run_non_deterministic_success(self, readnames, output_name,
                    dna_source=None):

        test_name = inspect.stack()[1][3]
        print('\n**** starting expected success test: ' + test_name + ' *****')
        print('   libs: ' + str(readnames))

        print("READNAMES: " + str(readnames))
        print("STAGED: " + str(self.staged))

        libs = [self.staged[n]['info'][1] for n in readnames]

        params = {'workspace_name': self.getWsName(),
                  'read_libraries': libs,
                  'output_contigset_name': output_name
                  }

        if not (dna_source is None):
            if dna_source == 'None':
                params['dna_source'] = None
            else:
                params['dna_source'] = dna_source

        ret = self.getImpl().run_SPAdes(self.ctx, params)[0]

        report = self.wsClient.get_objects([{'ref': ret['report_ref']}])[0]
        self.assertEqual('KBaseReport.Report', report['info'][2].split('-')[0])
        self.assertEqual(1, len(report['data']['objects_created']))
        self.assertEqual('Assembled contigs',
                         report['data']['objects_created'][0]['description'])
        self.assertIn('Assembled into ', report['data']['text_message'])
        self.assertIn('contigs', report['data']['text_message'])

        assembly_ref = report['data']['objects_created'][0]['ref']
        assembly = self.wsClient.get_objects([{'ref': assembly_ref}])[0]
        self.assertEqual('KBaseGenomeAnnotations.Assembly', assembly['info'][2].split('-')[0])
        self.assertEqual(output_name, assembly['info'][1])
