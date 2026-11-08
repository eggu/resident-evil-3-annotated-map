"""Marker name text: Korean '의' rule and two-line wrapping (RE0 HD map rules, 2026-11-07 default for every mod)."""
import re

# Game-specific keep-list: dropping '의' reads wrong here (the in-game title of the puzzle book).
KEEP_UI = {'지혜의 책'}
PARTICLE = re.compile(r'(?<=\S)의 ')


def ko_item(text):
    """'A의 B' -> 'A B' when natural: never inside a word ('의료 지침서'), never for a one-syllable stem."""
    if text in KEEP_UI:
        return text
    def drop(m):
        stem = text[:m.start()].split(' ')[-1]
        return m.group(0) if len(stem) < 2 else ' '
    return PARTICLE.sub(drop, text)


def name_lines(text):
    """One or two lines: 8 or more characters (spaces included) break at the space nearest the middle; a single
    word never splits."""
    if len(text) < 8 or ' ' not in text:
        return [text]
    parts = text.split(' ')
    at = min(range(1, len(parts)), key=lambda i: abs(len(' '.join(parts[:i])) - len(' '.join(parts[i:]))))
    return [' '.join(parts[:at]), ' '.join(parts[at:])]


if __name__ == '__main__':
    assert ko_item('다리오의 메모') == '다리오 메모' and ko_item('본부의 팩스') == '본부 팩스'
    assert ko_item('의료 지침서') == '의료 지침서' and ko_item('지혜의 책') == '지혜의 책'
    assert ko_item('돌의 반지') == '돌의 반지'   # one-syllable stem keeps its particle
    assert name_lines('Lockpick') == ['Lockpick'] and name_lines('Mine Thrower') == ['Mine', 'Thrower']
    assert name_lines('Mercenary\'s Pocketbook') == ['Mercenary\'s', 'Pocketbook'] and name_lines('S.T.A.R.S.Card') == ['S.T.A.R.S.Card']
    assert name_lines('Fax from Headquarters') == ['Fax from', 'Headquarters']
    print('labels OK')
