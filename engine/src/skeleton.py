# -*- coding: utf-8 -*-
"""skeleton.py — 시나리오 JSON 한 편의 **뼈대**를 조립한다.

조각(meta·background·cast·clue_graph·ui …)을 받아 스키마 순서대로 끼운다.
생성기(build_*.py)와 커스텀 생성기가 공통으로 쓴다.
"""


def skeleton(meta, background, adapted, trick, intro, victim, death, places,
             cast, clues, choices, solution):
    return {
        "meta": meta, "background": background, "adapted_story": adapted, "trick": trick,
        "intro": intro, "victim": victim, "death": death,
        "time_slots": ["초저녁", "밤", "새벽"],
        "map": {"max_move_per_slot": 999, "places": places},
        "cast": cast, "clue_graph": clues, "choices": choices,
        "answer_format": {"culprit": "choice", "weapon": "choice", "motive": "free_text"},
        "solution": solution,
        "config": {"suspects": 5, "rounds": 3, "attempts": 3, "turns_per_round": 8},
    }
