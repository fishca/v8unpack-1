import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

from . import helper
from .container_reader import extract as container_extract, decompress_and_extract
from .container_writer import build as container_build, compress_and_build
from .decoder import decode, encode
from .ext_exception import ExtException
from .file_organizer import FileOrganizer
from .file_organizer_ce import FileOrganizerCE
from .helper import update_dict
from .index import update_index
from .json_container_decoder import json_decode, json_encode
from .version import __version__


def _load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise Exception(f'Error: Bad index file - not dict\n')
        return data
    except FileNotFoundError:
        raise Exception(f'Error: index file not found - {filename}')
    except Exception as err:
        raise Exception(f'Error: Bad index file - {err}\n')


def _check_index(index_filename):
    if index_filename:
        index = []
        _index = _load_json(index_filename)
        sub_index = _index.pop('index.json', None)
        if sub_index:
            for elem in sub_index:
                index.append(_load_json(elem))
        index.append(_index)
        data = update_dict(*index)
        return data
    return None


def extract(in_filename: str, out_dir_name: str, *, temp_dir=None, index=None, version=None, descent=None):
    try:
        begin0 = datetime.now()
        print(f"v8unpack {__version__}")

        index = _check_index(index)
        if not index and index is not None:
            return

        print(f"Начали")

        if descent is None:
            helper.clear_dir(os.path.normpath(out_dir_name))
        clear_temp_dir = False
        if temp_dir is None:
            clear_temp_dir = True
            temp_dir = tempfile.mkdtemp()
        helper.clear_dir(os.path.normpath(temp_dir))

        dir_stage0 = os.path.join(temp_dir, 'decode_stage_0')
        dir_stage1 = os.path.join(temp_dir, 'decode_stage_1')
        dir_stage2 = os.path.join(temp_dir, 'decode_stage_2')
        dir_stage3 = os.path.join(temp_dir, 'decode_stage_3')

        pool = helper.get_pool()

        container_extract(in_filename, dir_stage0, False, False)
        decompress_and_extract(dir_stage0, dir_stage1, pool=pool)

        json_decode(dir_stage1, dir_stage2, pool=pool)

        decode(dir_stage2, dir_stage3, pool=pool, version=version)

        if descent:
            FileOrganizerCE.unpack(dir_stage3, out_dir_name, pool=pool, index=index, descent=int(descent))
        else:
            FileOrganizer.unpack(dir_stage3, out_dir_name, pool=pool, index=index)

        end = datetime.now()
        print(f'{"Готово":30}: {end - begin0}')

        helper.close_pool(pool)
        if clear_temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as err:
        error = ExtException(parent=err)
        print(f'\n\n{error}')


def build(in_dir_name: str, out_file_name: str, *, temp_dir=None, index=None,
          version='803', descent=None, gui=None, **kwargs):
    try:
        begin0 = datetime.now()

        print(f"v8unpack {__version__}")

        index = _check_index(index)
        if not index and index is not None:
            return

        print(f"Начали")

        clear_temp_dir = False
        if temp_dir is None:
            clear_temp_dir = True
            temp_dir = tempfile.mkdtemp()
        helper.clear_dir(os.path.normpath(temp_dir))

        dir_stage0 = os.path.join(temp_dir, 'encode_stage_0')
        dir_stage1 = os.path.join(temp_dir, 'encode_stage_1')
        dir_stage2 = os.path.join(temp_dir, 'encode_stage_2')
        dir_stage3 = os.path.join(temp_dir, 'encode_stage_3')

        pool = helper.get_pool(processes=1)

        if descent:
            FileOrganizerCE.pack(in_dir_name, dir_stage3, pool=pool, index=index, descent=int(descent))
        else:
            FileOrganizer.pack(in_dir_name, dir_stage3, pool=pool, index=index)

        encode(dir_stage3, dir_stage2, version=version, pool=pool, gui=gui,
               file_name=os.path.basename(out_file_name), **kwargs)

        json_encode(dir_stage2, dir_stage1, pool=pool)

        compress_and_build(dir_stage1, dir_stage0, pool=pool)
        container_build(dir_stage0, out_file_name, True)

        helper.close_pool(pool)
        if clear_temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

        end = datetime.now()
        print(f'{"Готово":30}: {end - begin0}')

    except Exception as err:
        error = ExtException(parent=err)
        print(f'\n\n{error}')


def build_all(product_file_name: str, product_code: str = None):
    try:
        products = _load_json(os.path.abspath(product_file_name))
        if product_code:
            products = [products[product_code]]
        for product, params in products.items():
            print(f'\nСобираем {product}\n')
            build(
                params['src'], params['bin'],
                temp_dir=params.get('temp'), index=params.get('index'),
                version=params.get('version'), descent=params.get('descent'),
                gui=params.get('gui')
            )
        pass
    except Exception as err:
        error = ExtException(parent=err)
        print(f'\n\n{error}')


def extract_all(product_file_name: str, product_code: str = None):
    try:
        products = _load_json(product_file_name)
        if product_code:
            products = [products[product_code]]
        for product, params in products.items():
            print(f'\nСобираем {product}\n')
            extract(
                params['bin'], params['src'],
                temp_dir=params.get('temp'), index=params.get('index'),
                version=params.get('version'), descent=params.get('descent')
            )
        pass
    except Exception as err:
        error = ExtException(parent=err)
        print(f'\n\n{error}')


def main():
    parser = argparse.ArgumentParser(
        prog=f'v8unpack {__version__}',
        description='Распаковка и сборка бинарных файлов 1С'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-E', nargs=2, metavar=('file', 'src'),
                       help='разобрать файл 1С, где '
                            'file - путь до бинарного файла, '
                            'src -  папка куда будут помещены исходники')
    group.add_argument('-B', nargs=2, metavar=('src', 'file'),
                       help='собрать файл 1С, где '
                            'src - путь до папки с исходниками, '
                            'file - путь до бинарного файла')
    group.add_argument('-I', nargs=1, metavar='src',
                       help='сформировать index, где '
                            'src - путь до папки с исходниками'
                       )
    parser.add_argument('--temp', help='путь до временной папки')
    parser.add_argument('--core', help='название общей папки добавляемой в индекс по умолчанию')
    parser.add_argument('--index', help='путь до json файла с словарем копирования,'
                                        'структура файла: {путь исходника: путь общей папки}')
    parser.add_argument('--version', default='803',
                        help="версия сборки, для сборки обработок указывается версия платформы 801/802/803, "
                             " для сборки расширений указывается версия режима совместимости, "
                             "например для 8.3.6 это 80306, подробности в документации на github")
    parser.add_argument('--descent',
                        help="включает режим наследования при сборке и разборке,"
                             "четырех значный формат 3.0.75.100 (не более 3 знаков на каждый разряд)"
                             "подробности в инструкции - раздел разработка расширений")
    parser.add_argument('--gui',
                        help="режим совместимости интерфейса 1С, переопределяет значение из исходников "
                             "для расширений, если указан устанавливается в соответствующий реквизит. "
                             "Допустимые значения:"
                             " допустимые значения 0 - Версия 8.2, 1 - Версия 8.2. Разрешить Такси,"
                             " 2- Такси. Разрешить Версия 8.2, 3 - Такси"
                             "для расширений устанавливается в соответствующий реквизит")

    group.add_argument('-EA', nargs=1, metavar=('file', 'src'),
                       help='разобрать файл 1С, используя параметры из списка продуктов '
                            'file - путь до файла со списком продуктов и их параметрами, '
                            'code - код продукта из файла, если не указан будут разобраны все найденные файлы продуктов')
    group.add_argument('-BA', nargs=1, metavar=('file', 'src'),
                       help='собрать файл 1С, параметры сборки из списка продуктов, где '
                            'file - путь до файла со списком продуктов и их параметрами, '
                            'code -  папка куда будут помещены исходники')

    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    args = parser.parse_args()
    gui = args.gui if args.gui else None

    if args.E is not None:
        extract(os.path.abspath(args.E[0]), os.path.abspath(args.E[1]),
                index=args.index, temp_dir=args.temp, version=args.version, descent=descent)
        return

    if args.B is not None:
        build(os.path.abspath(args.B[0]), os.path.abspath(args.B[1]),
              index=args.index, temp_dir=args.temp, version=args.version, descent=descent, gui=gui)
        return

    if args.BA is not None:
        build_all(*args.BA)
        return

    if args.EA is not None:
        extract_all(*args.EA)
        return

    if args.I is not None:
        update_index(args.I[0], args.index, args.core)
        return


if __name__ == '__main__':
    sys.exit(main())
