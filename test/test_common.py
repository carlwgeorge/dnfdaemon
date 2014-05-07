# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath('dnfdaemon'))

import support
import common
import json
import logging


class DnfBaseMock(common.DnfBase):

    def __init__(self, parent):
        self._base = support.MockBase('main')
        self.parent = parent
        self.md_progress = common.MDProgress(parent)
        self.progress = common.Progress(parent, max_err=100)
        self._packages = None

    def setup_base(self):
        self._packages = common.Packages(self._base)

    def __getattr__(self, attr):
        if hasattr(self._base, attr):
            return getattr(self._base, attr)
        else:
            raise AttributeError


class TestPackages(support.TestCase):

    def test_packages(self):
        """Test Packages()"""
        base = support.MockBase('main')
        pkgs = common.Packages(base)
        inst = list(map(str, pkgs.installed))
        self.assertItemsEqual(inst, ['bar-1.0-1.noarch',
                                'foo-1.0-1.noarch',
                                'bar-old-1.0-1.noarch'])
        avail = list(map(str, pkgs.available))
        self.assertItemsEqual(avail, ['bar-2.0-1.noarch',
                                 'foo-2.0-1.noarch',
                                 'foo-dep-err-1.0-1.noarch',
                                 'bar-dep-err-1.0-1.noarch',
                                 'bar-new-2.0-1.noarch',
                                 'petzoo-1.0-1.noarch'])
        upds = list(map(str, pkgs.updates))
        self.assertItemsEqual(upds, ['bar-2.0-1.noarch',
                                'foo-2.0-1.noarch'])
        obs = list(map(str, pkgs.obsoletes))
        self.assertItemsEqual(obs, ['bar-new-2.0-1.noarch'])


class TestDnfBase(support.TestCase):

    def setUp(self):
        self.base = DnfBaseMock(None)
        self.base.setup_base()

    def test_packages_attr(self):
        """Test packages attr"""
        self.assertIsInstance(self.base.packages, common.Packages)

    def test_search_nodups(self):
        """Test search (nodups)"""
        found = self.base.search(['name'], ['foo'], showdups=False)
        res = list(map(str, found))
        self.assertItemsEqual(res, ['foo-2.0-1.noarch',
                               'foo-dep-err-1.0-1.noarch'])

    def test_search_dups(self):
        """Test search (dups)"""
        found = self.base.search(['name'], ['foo'], showdups=True)
        res = list(map(str, found))
        self.assertItemsEqual(res, ['foo-2.0-1.noarch',
                               'foo-dep-err-1.0-1.noarch',
                               'foo-1.0-1.noarch',
                               'foo-1.0-1.noarch'])


class TestCommonBase(support.TestCase):

    def _get_base(self, reset=False, load_sack=True):
        if not self._base or reset:
            self._base = DnfBaseMock(self)
            if load_sack:
                self._base.setup_base()
        return self._base

    def setUp(self):
        common.doTextLoggerSetup(logroot='dnf', loglvl=logging.DEBUG)
        self._base = None
        self.daemon = common.DnfDaemonBase()
        self.daemon._base = self._get_base()


class TestCommonMisc(TestCommonBase):

    def test_base(self):
        """Test Packages class"""
        base = self.daemon.base
        self.assertIsNotNone(base)

    def test_search_with_attr_all(self):
        """Test search_with_attr (all)"""
        fields = ['name']
        keys = ['bar']
        attrs = []
        match_all = True
        newest_only = False
        tags = False
        found = self.daemon._search_with_attr(fields, keys, attrs,
                                              match_all, newest_only,
                                              tags)
        self.assertItemsEqual(json.loads(found),
            ['bar,0,1.0,1,noarch,@System',
             'bar-old,0,1.0,1,noarch,@System',
             'bar,0,1.0,1,noarch,main',
             'bar-old,0,1.0,1,noarch,main',
             'bar,0,2.0,1,noarch,main',
             'bar-dep-err,0,1.0,1,noarch,main',
             'bar-new,0,2.0,1,noarch,main'])

    def test_search_with_attr_new(self):
        """Test search_with_attr (newest)"""
        fields = ['name']
        keys = ['bar']
        attrs = []
        match_all = True
        newest_only = True
        tags = False
        found = self.daemon._search_with_attr(fields, keys, attrs,
                                              match_all, newest_only,
                                              tags)
        self.assertItemsEqual(json.loads(found),
            ['bar-old,0,1.0,1,noarch,@System',
             'bar,0,2.0,1,noarch,main',
             'bar-dep-err,0,1.0,1,noarch,main',
             'bar-new,0,2.0,1,noarch,main'])

    def test_get_packages_by_name_with_attr(self):
        """Test get_packages_by_name_with_attr"""
        attrs = []
        pkgs = self.daemon._get_packages_by_name_with_attr('foo', attrs, True)
        self.assertItemsEqual(json.loads(pkgs), ["foo,0,2.0,1,noarch,main"])
        pkgs = self.daemon._get_packages_by_name_with_attr('foo', attrs, False)
        self.assertEqual(json.loads(pkgs),
            ["foo,0,2.0,1,noarch,main",
             "foo,0,1.0,1,noarch,@System"])
        pkgs = self.daemon._get_packages_by_name_with_attr('*dep*',
                                                           attrs, True)
        self.assertItemsEqual(json.loads(pkgs),
            ["foo-dep-err,0,1.0,1,noarch,main",
             "bar-dep-err,0,1.0,1,noarch,main"])


class TestCommonGroups(TestCommonBase):

    def setUp(self):
        TestCommonBase.setUp(self)
        self.daemon.base.conf.debuglevel = 9
        self.daemon.base.read_mock_comps()

    def test_get_group_pkgs(self):
        """Test get_group_pkgs"""
        grp_id = 'test-grp'
        grp_flt = 'all'
        fields = []
        pkgs = self.daemon._get_group_pkgs(grp_id, grp_flt, fields)
        self.assertItemsEqual(json.loads(pkgs),
            ['bar,0,2.0,1,noarch,main', 'petzoo,0,1.0,1,noarch,main'])
        grp_flt = ''
        pkgs = self.daemon._get_group_pkgs(grp_id, grp_flt, fields)
        self.assertItemsEqual(json.loads(pkgs),
            ['petzoo,0,1.0,1,noarch,main'])

    def test_group_install(self):
        cmds = "test-grp"
        res = self.daemon._group_install(cmds)
        print(json.loads(res))
        self.assertItemsEqual(json.loads(res),
        [True, [['install', [['petzoo,0,1.0,1,noarch,main', 0.0, []]]]]])