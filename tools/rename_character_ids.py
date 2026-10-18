#!/usr/bin/env python3
"""名前別CSVからキャラIDを一括変更する。標準ではプレビューのみ。"""
import argparse
import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def records(path):
    return list(csv.reader(path.read_bytes().decode('utf-8-sig').splitlines()))


def inventory(root):
    result = {}
    for path in sorted((root / 'chara').rglob('*')):
        if path.suffix.lower() != '.csv':
            continue
        rows = records(path)
        ids = [int(r[1]) for r in rows if len(r) > 1 and r[0].strip() == '番号']
        names = [r[1] for r in rows if len(r) > 1 and r[0].strip() == '名前']
        if len(ids) != 1 or len(names) != 1 or ids[0] in result:
            raise ValueError(f'番号・名前が不正または番号が重複: {path}')
        match = re.fullmatch(r'Chara(\d+)(.*)\.csv', path.name, re.I)
        if not match or int(match[1]) != ids[0]:
            raise ValueError(f'ファイル名と番号が不一致: {path}')
        result[ids[0]] = (names[0], path, match[2])
    return result


def plan(root, list_path):
    chars = inventory(root)
    names = {}
    for current_id, (name, _, _) in chars.items():
        if name in names:
            raise ValueError(f'キャラ名が重複しているため判定できません: {name}')
        names[name] = current_id
    mapping = {}
    seen = set()
    with list_path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ['キャラ名', '変更後ID']:
            raise ValueError('列は「キャラ名,変更後ID」にしてください')
        for row in reader:
            name = row['キャラ名']
            if name in seen:
                raise ValueError(f'キャラ名が重複: {name}')
            seen.add(name)
            if name not in names:
                raise ValueError(f'キャラ名が見つかりません: {name}')
            old = names[name]
            value = row['変更後ID'].strip()
            if not value:
                continue
            if not re.fullmatch(r'[0-9]+', value) or not 0 <= int(value) <= 999:
                raise ValueError(f'変更後IDは0～999: {row}')
            if int(value) != old:
                mapping[old] = int(value)
    final_ids = [mapping.get(n, n) for n in chars]
    if len(final_ids) != len(set(final_ids)):
        raise ValueError('変更後IDが他のキャラと重複します。入れ替えの場合は両方指定してください')
    cstr = root / 'CSTR.csv'
    cstr_rows = records(cstr)
    cstr_ids = [int(r[0]) for r in cstr_rows if r and r[0].strip().isdigit()]
    for old in mapping:
        matches = [r for r in cstr_rows if len(r) > 1 and r[0].strip() == str(1000 + old)]
        if len(matches) != 1 or matches[0][1] != chars[old][0]:
            raise ValueError(f'CSTRのID・名前が一致しません: {old} {chars[old][0]}')
    cm = {1000 + a: 1000 + b for a, b in mapping.items()}
    finals = [cm.get(n, n) for n in cstr_ids]
    if len(finals) != len(set(finals)):
        raise ValueError('CSTRの変更後IDが重複します')

    changes = []
    for path in [v[1] for v in chars.values()] + [cstr]:
        original = path.read_bytes()
        # バイト列を直接編集し、BOM・改行・コメントを保持する。
        def replace(match):
            key, number = match[1], int(match[2])
            table = cm if path == cstr or key.strip() == b'CSTR' else mapping
            return key + b',' + str(table.get(number, number)).encode() + match[3] if number in table else match[0]
        if path == cstr:
            pattern = rb'(?m)^()(\d+)(?=,)'
            data = re.sub(pattern, lambda m: str(cm[int(m[2])]).encode() if int(m[2]) in cm else m[0], original)
        else:
            keys = '|'.join(['番号', '相性', ';相性', 'CSTR']).encode()
            bom = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
            data = bom + re.sub(rb'(?m)^(' + keys + rb'),([0-9]+)([ \t]*)(?=,|\r?$)', replace, original[len(bom):])
        destination = path
        for old, (name, source, suffix) in chars.items():
            if source == path and old in mapping:
                destination = path.with_name(f'Chara{mapping[old]:03d}{suffix}.csv')
        if data != original or destination != path:
            changes.append((path, destination, data))
    return mapping, chars, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', type=Path, default=ROOT / 'character_id_map.csv')
    parser.add_argument('--apply', action='store_true', help='バックアップ後に書き換える')
    args = parser.parse_args()
    try:
        mapping, chars, changes = plan(ROOT, args.list)
        for old, new in sorted(mapping.items()):
            print(f'{chars[old][0]}: {old:03d} → {new:03d} / CSTR {1000+old} → {1000+new}')
        print(f'変更対象: {len(mapping)}人、{len(changes)}ファイル')
        if not changes or not args.apply:
            if changes:
                print('プレビューのみです。反映するには --apply を指定してください。')
            return
        backup = ROOT / 'id_backups' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup.mkdir(parents=True)
        shutil.copy2(args.list, backup / 'replacement_list.csv')
        for source, destination, data in changes:
            target = backup / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        # 全入力をメモリに保持してから削除・書き出すため、連鎖置換とID交換に対応する。
        try:
            for source, _, _ in changes:
                source.unlink()
            for _, destination, data in changes:
                destination.write_bytes(data)
        except Exception:
            for _, destination, _ in changes:
                if destination.exists():
                    destination.unlink()
            for source, _, _ in changes:
                shutil.copy2(backup / source.relative_to(ROOT), source)
            raise
        print(f'反映しました。バックアップ: {backup}')
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'エラー: {exc}\n')


if __name__ == '__main__':
    main()
