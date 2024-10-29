from __future__ import print_function
import unittest
import os
import time
import json

from os import environ
from configparser import ConfigParser
import psutil
from pprint import pprint
import shutil
import inspect
import requests

from installed_clients.AbstractHandleClient import AbstractHandle as HandleService
from kb_unicycler.kb_unicyclerImpl import kb_unicycler
from installed_clients.ReadsUtilsClient import ReadsUtils
from installed_clients.AssemblyUtilClient import AssemblyUtil
from kb_unicycler.kb_unicyclerServer import MethodContext
from installed_clients.WorkspaceClient import Workspace
from installed_clients.DataFileUtilClient import DataFileUtil

class unicyclerTest(unittest.TestCase):

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
                            {'service': 'kb_unicycler',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_unicycler'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.cfg["SDK_CALLBACK_URL"] = cls.callbackURL
        cls.cfg["KB_AUTH_TOKEN"] = cls.token
        cls.wsURL = cls.cfg['workspace-url']
        cls.shockURL = cls.cfg['shock-url']
        cls.hs = HandleService(url=cls.cfg['handle-service-url'],
                               token=cls.token)
        # cls.wsClient = workspaceService(cls.wsURL, token=cls.token)
        cls.wsClient = Workspace(cls.wsURL, token=cls.token)
        wssuffix = int(time.time() * 1000)
        wsName = "test_kb_unicycler_" + str(wssuffix)
        cls.wsinfo = cls.wsClient.create_workspace({'workspace': wsName})
        print('created workspace ' + cls.getWsName())

        cls.PROJECT_DIR = 'unicycler_outputs'
        cls.scratch = cls.cfg['scratch']
        if not os.path.exists(cls.scratch):
            os.makedirs(cls.scratch)
        cls.prjdir = os.path.join(cls.scratch, cls.PROJECT_DIR)
        if not os.path.exists(cls.prjdir):
            os.makedirs(cls.prjdir)
        cls.serviceImpl = kb_unicycler(cls.cfg)

        cls.readUtilsImpl = ReadsUtils(cls.callbackURL, token=cls.token)
        cls.assy_util = AssemblyUtil(cls.callbackURL, token=cls.token)
        cls.dfuClient = DataFileUtil(url=cls.callbackURL, token=cls.token)
        cls.staged = {}
        cls.nodes_to_delete = []
        cls.handles_to_delete = []
        cls.setupTestData()
        print('\n\n=============== Starting Unicycler tests ==================')

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
            if cls.handles_to_delete:
                cls.hs.delete_handles(cls.hs.hids_to_handles(cls.handles_to_delete))
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

    @classmethod
    def upload_file_to_shock_and_get_handle(cls, test_file):
        '''
        Uploads the file in test_file to shock and returns the node and a
        handle to the node.
        '''
        print('loading file to shock: ' + test_file)

        temp_file = cls.move_test_file_to_shared_scratch(test_file)
        fts = cls.dfuClient.file_to_shock({'file_path': temp_file,
                                           'make_handle': True})

        cls.nodes_to_delete.append(fts['shock_id'])
        cls.handles_to_delete.append(fts['handle']['hid'])

        return fts['shock_id'], fts['handle']['hid'], fts['size']

    @classmethod
    def move_test_file_to_shared_scratch(cls, test_file):
        # file can't be in /kb/module/test or dfu won't find it
        temp_file = os.path.join("/kb/module/work/tmp", os.path.basename(test_file))
        shutil.copy(os.path.join("/kb/module/test", test_file), temp_file)
        return temp_file

    @classmethod
    def upload_reads(cls, wsobjname, object_body, fwd_reads,
                     rev_reads=None, single_end=False, sequencing_tech='Illumina',
                     single_genome='1'):

        ob = dict(object_body)  # copy
        ob['sequencing_tech'] = sequencing_tech
        ob['wsname'] = cls.getWsName()
        ob['name'] = wsobjname
        if single_end or rev_reads:
            ob['interleaved'] = 0
        else:
            ob['interleaved'] = 1
        print('\n===============staging data for object ' + wsobjname +
              '================')
        print('uploading forward reads file ' + fwd_reads['file'])
        fwd_id, fwd_handle_id, fwd_size = \
            cls.upload_file_to_shock_and_get_handle(fwd_reads['file'])

        ob['fwd_id'] = fwd_id
        rev_id = None
        rev_handle_id = None
        if rev_reads:
            print('uploading reverse reads file ' + rev_reads['file'])
            rev_id, rev_handle_id, rev_size = \
                cls.upload_file_to_shock_and_get_handle(rev_reads['file'])
            ob['rev_id'] = rev_id
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
    def upload_assembly(cls, wsobjname, file, name):
        file = cls.move_test_file_to_shared_scratch(file)
        cls.assy_util.save_assembly_from_fasta2({
            "file": {
                "path": file,
                "assembly_name": name
            },
            "workspace_id": cls.wsinfo[0],
            "assembly_name": wsobjname,
            "type": "isolate",
            # ideally would set other fields here if this was an actual upload
        })

    @classmethod
    def setupTestData(cls):
        print('Shock url ' + cls.shockURL)
        # print('WS url ' + cls.wsClient.url)
        # print('Handle service url ' + cls.hs.url)
        print('CPUs detected ' + str(psutil.cpu_count()))
        print('Available memory ' + str(psutil.virtual_memory().available))
        print('staging data')

        fwd_reads = {'file': 'data/short_reads_1.fastq.gz',
                     'name': 'short_reads_1.fastq.gz',
                     'type': 'fastq'}
        rev_reads = {'file': 'data/short_reads_2.fastq.gz',
                     'name': 'short_reads_2.fastq.gz',
                     'type': ''}
        long_reads_low_depth = {'file': 'data/long_reads_low_depth.fastq.gz',
                     'name': 'long_reads_low_depth.fastq.gz',
                     'type': ''}
        long_reads_high_depth = {'file': 'data/long_reads_high_depth.fastq.gz',
                     'name': 'long_reads_high_depth.fastq.gz',
                     'type': ''}
        cls.upload_reads('shigella_short', {'single_genome': 1}, fwd_reads, rev_reads=rev_reads)
        cls.upload_reads('shigella_long_low', {'single_genome': 1}, long_reads_low_depth,
                         single_end=True, sequencing_tech="PacBio")
        cls.upload_reads('shigella_long_high', {'single_genome': 1}, long_reads_high_depth,
                         single_end=True, sequencing_tech="PacBio")
        cls.upload_assembly(
            'shigella_assy',
            'data/long_reads_high_depth_headers_fixed.fasta.gz',
            'long_reads_high_depth.fasta.gz'
        )
        print('Data staged.')

    @classmethod
    def make_ref(self, object_info):
        return str(object_info[6]) + '/' + str(object_info[0]) + \
            '/' + str(object_info[4])

    def run_unicycler(self,
                      output_contigset_name,
                      short_paired_libraries=None,
                      short_unpaired_libraries=None,
                      long_reads_library=None,
                      min_contig_length=100,
                      min_long_read_length=100,
                      num_linear_seqs=0,
                      bridging_mode="normal"):
        """
        run_unicycler: The main method to test all possible input data sets
        """
        test_name = inspect.stack()[1][3]
        print('\n**** starting expected success test: ' + test_name + ' *****')

        print("SHORT_PAIRED: " + str(short_paired_libraries))
        print("SHORT_UNPAIRED: " + str(short_unpaired_libraries))
        print("LONG: " + str(long_reads_library))
        print("STAGED: " + str(self.staged))

        params = {'workspace_name': self.getWsName(),
                  'short_paired_libraries': short_paired_libraries,
                  'short_unpaired_libraries': short_unpaired_libraries,
                  'long_reads_library': long_reads_library,
                  'output_contigset_name': output_contigset_name,
                  'min_contig_length': min_contig_length,
                  'min_long_read_length': min_long_read_length,
                  'num_linear_seqs': num_linear_seqs,
                  'bridging_mode': bridging_mode,
                  'no_correct': 1
                  }

        ret = self.getImpl().run_unicycler(self.ctx, params)[0]
        self.assertReportAssembly(ret, output_contigset_name)

    def assertReportAssembly(self, ret_obj, assembly_name):
        """
        assertReportAssembly: given a report object, check the object existence
        """
        report = self.wsClient.get_objects2({
                        'objects': [{'ref': ret_obj['report_ref']}]})['data'][0]
        self.assertEqual('KBaseReport.Report', report['info'][2].split('-')[0])
        self.assertEqual(1, len(report['data']['objects_created']))
        self.assertEqual('Assembled contigs',
                         report['data']['objects_created'][0]['description'])
        self.assertIn('Assembled into ', report['data']['text_message'])
        self.assertIn('contigs', report['data']['text_message'])
        print("**************Report Message*************\n")
        print(report['data']['text_message'])

        assembly_ref = report['data']['objects_created'][0]['ref']
        assembly = self.wsClient.get_objects([{'ref': assembly_ref}])[0]

        self.assertEqual('KBaseGenomeAnnotations.Assembly', assembly['info'][2].split('-')[0])
        self.assertEqual(1, len(assembly['provenance']))
        self.assertEqual(assembly_name, assembly['data']['assembly_id'])

        temp_handle_info = self.hs.hids_to_handles([assembly['data']['fasta_handle_ref']])
        assembly_fasta_node = temp_handle_info[0]['id']
        self.nodes_to_delete.append(assembly_fasta_node)

    # Uncomment to skip this test
    # @unittest.skip("skipped test test_shigella_short_kbfile")
    def test_shigella_short_kbfile(self):
        self.run_unicycler( 'shigella_short_out',
                            short_paired_libraries=['shigella_short'])

    # Uncomment to skip this test
    # doesn't work due to miniasm not getting a result
    @unittest.skip("skipped test test_shigella_long_kbfile")
    def test_shigella_long_kbfile(self):
        self.run_unicycler( 'shigella_long_out',
                            long_reads_library='shigella_long_high')

    # Uncomment to skip this test
    # @unittest.skip("skipped test test_shigella_hybrid_low_kbfile")
    def test_shigella_hybrid_low_kbfile(self):
        self.run_unicycler( 'shigella_hybrid_low_out',
                            short_paired_libraries=['shigella_short'],
                            long_reads_library='shigella_long_low')

    # Uncomment to skip this test
    # @unittest.skip("skipped test test_shigella_hybrid_high_kbfile")
    def test_shigella_hybrid_high_kbfile(self):
        self.run_unicycler( 'shigella_hybrid_high_out',
                            short_paired_libraries=['shigella_short'],
                            long_reads_library='shigella_long_high')

    # Uncomment to skip this test
    # @unittest.skip("skipped test test_shigella_hybrid_with_assembly")
    def test_shigella_hybrid_with_assembly(self):
        self.run_unicycler( 'shigella_hybrid_assembly_out',
                            short_paired_libraries=['shigella_short'],
                            long_reads_library='shigella_assy')

    # ########################End of passed tests######################
