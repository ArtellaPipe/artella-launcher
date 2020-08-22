#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, absolute_import

__author__ = "Tomas Poveda"
__license__ = "MIT"
__maintainer__ = "Tomas Poveda"
__email__ = "tpovedatd@gmail.com"

import os
import argparse
import importlib

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Python Virtual Environment to generate launcher')
    parser.add_argument('--project-name', type=str, required=True)
    parser.add_argument('--tag', type=str, required=False, default='DEV')
    parser.add_argument('--install-path', type=str, required=True)
    parser.add_argument('--paths-to-register', nargs='+', type=str, required=False)
    parser.add_argument('--artellapipe-configs-path', type=str, required=False)
    parser.add_argument('--dev', required=False, default=False, action='store_true')
    args = parser.parse_args()

    import tpDcc.loader
    tpDcc.loader.init(dev=args.dev)

    import artellapipe.loader
    artellapipe.loader.init(dev=args.dev)

    import artellapipe
    loader_mod = importlib.import_module('{}.loader'.format(args.project_name))

    artella_configs_path = args.artellapipe_configs_path
    if artella_configs_path and os.path.isdir(artella_configs_path):
        os.environ['ARTELLA_CONFIGS_PATH'] = artella_configs_path

    loader_mod.init(dev=args.dev)
    from artellapipe.launcher import loader
    loader.init()
    from artellapipe.launcher.core import launcher
    launcher.run(project=getattr(artellapipe, args.project_name),
                 install_path=args.install_path, paths_to_register=args.paths_to_register,
                 tag=args.tag, dev=args.dev)
