# -*- coding: utf-8 -*-
"""stress_hf.py — dsl04 GPU에서 실제 모델로 용의자 에이전트를 몰아붙이는 자기완결형 스크립트.
시나리오 1편이 이 파일에 내장돼 있고, transformers로 모델을 올려 5명을 심문한다.
매 턴: 응답 + 지연(초·tok/s) + 실시간 QA 플래그(자백누출/무고자자백/비밀조기누설/지식경계/모순/말투이탈).
사용:  export HOME=/mnt/data1/dsl04;  python stress_hf.py
       (MM_MOCK=1 이면 모델 없이 배관만 점검)"""
import json, time, re, os, sys
SCENARIO = json.loads(r"""{"meta": {"origin": "나생문(라쇼몽·곤자쿠 설화)", "era": "옛 도읍 말기", "title": "성문 아래 쇠갈고리"}, "background": {"setting_raw": {"era": "기근이 든 옛 도읍 말기", "location": "허물어진 성문 나생문 — 시체와 유민이 뒤엉킨 폐허", "culture": "동아시아 고도(古都)"}}, "time_slots": ["초저녁", "밤", "새벽"], "death": {"time_slot": "밤", "place": "PC", "place_name": "성문 누각 아래(현장)"}, "victim": {"name": "노파"}, "place_names": {"PC": "성문 누각 아래(현장)", "P1": "누각 서편 계단(사부로 자리)", "P2": "성문 동쪽 처마(만수 자리)", "P3": "성벽 안쪽 토굴(옥이 자리)", "P4": "무덤가 움막(칠성 자리)", "P5": "저자터 곡식 수레(덕배 자리)"}, "decisive_surface": "현장 진흙을 파 보면: 무덤 진창 특유의 짚신 자국, 시체용 쇠갈고리 끝자국, 그리고 노파 손톱 밑 살점이 칠성의 옆구리 생채기와 맞는다.", "cast": [{"id": "C1", "name": "사부로", "public": "주군을 잃은 낭인", "is_culprit": false, "persona": {"personality": "자존심 세고 완고하나 속은 무르다", "speech_style": "뻣뻣한 하오체", "example_lines": ["무사는 굶어도 남의 목을 갈고리로 찍진 않소.", "나는 밤새 서편 계단을 지켰소. 곁의 유민 여럿이 나를 보았을 거요."]}, "life_story": "사부로는 이름난 무가의 아랫무사로, 창칼을 배우며 주군을 섬기는 것을 삶의 전부로 알고 자랐다. 그러나 전란의 한복판에서 주군의 진이 무너지던 밤, 그는 겁에 질려 주군을 버리고 홀로 달아났다. 그 후로 어느 가문도 그를 거두지 않았고, 그는 녹슨 칼 한 자루만 품은 채 기근의 도읍을 떠돌다 나생문 아래로 흘러들었다. 굶주림에도 그는 무사의 체면을 놓지 못해, 남의 것을 훔치느니 굶기를 택했다. 노파가 그 칼을 담보로 잡고 '무사가 다 뭐냐' 조롱했을 때 그는 이를 갈았으나, 사람을 시체 다루듯 갈고리로 찍는 짓만은 그의 자존심이 허락하지 않았다. 그는 그 밤도 서편 계단에서 젖은 거적을 뒤집어쓰고, 잃어버린 주군과 저버린 자신을 곱씹으며 뜬눈으로 앉아 있었다.", "secret": {"text": "싸움에서 주군을 버리고 홀로 달아난 낭인이다", "type": "비겁·도주"}, "timeline": {"초저녁": "P1", "밤": "P1", "새벽": "P1"}, "alibi_narration": "나는 밤새 서편 계단을 지켰소. 곁의 유민 여럿이 나를 보았을 거요.", "knows": ["나는 그 밤(밤) 누각 서편 계단(사부로 자리)에 있었다.", "내 감춘 사정: 싸움에서 주군을 버리고 홀로 달아난 낭인이다.", "노파에 대한 내 감정: 무사의 체면을 짓밟힌 데 대한 분노."], "does_not_know": ["그 밤 사건 현장(성문 누각 아래(현장))에서 실제로 무슨 일이 있었는지.", "진범이 누구인지, 결정적 증거가 무엇인지는 알지 못한다.", "다른 용의자들이 각자 감추고 있는 비밀의 구체적 내용."], "pressure_points": [{"trigger": ["주군", "달아", "도주", "버리고", "비겁"], "reveals": "…그렇소, 나는 주군을 버리고 달아난 비겁한 놈이오. 그 죄로 이 꼴이 됐지. 허나 그 부끄러움 때문에라도, 나는 이 이상 비겁한 짓은 못 하오."}], "lies": []}, {"id": "C2", "name": "만수", "public": "쫓겨난 하인", "is_culprit": false, "persona": {"personality": "눈치 빠르고 방어적이다", "speech_style": "움츠린 하오체", "example_lines": ["소문은 소문이고, 사람 목숨은 목숨이오. 나는 그 밤 처마 밑에 있었소.", "초저녁엔 성문 아래서 불을 쬐다가, 밤엔 동쪽 처마로 자리를 옮겨 봇짐을 안고 잤소."]}, "life_story": "만수는 어려서 부모를 잃고 부잣집에 팔려 가 잔심부름부터 시작한 하인이다. 십수 년을 성실히 부렸으나, 곳간의 은그릇이 없어진 날 주인은 가장 만만한 그를 도둑으로 몰았다. 사실 그는 굶주린 누이를 먹이려 정말로 은그릇 하나를 훔쳐 봇짐에 감춰 두었고, 그 죄책감과 억울함이 뒤엉킨 채 집에서 내쫓겼다. 나생문 아래로 흘러든 그를, 노파는 '저놈이 도둑이다' 저자에 소문내어 어느 곳에서도 품을 팔지 못하게 만들었다. 그는 노파를 미워해 밤마다 성문을 서성였고, 그래서 사건이 나자 가장 먼저 의심을 샀다. 그러나 그는 물건을 훔치는 손이지, 사람을 시체 다루듯 갈고리로 찍는 손은 아니었다. 그 밤 그는 초저녁 화톳불 곁에 있다가, 밤이 깊자 봇짐을 안고 동쪽 처마로 물러나 웅크렸다.", "secret": {"text": "주인집 은그릇을 정말로 훔쳐 봇짐에 숨기고 있다", "type": "절도"}, "timeline": {"초저녁": "PC", "밤": "P2", "새벽": "P2"}, "alibi_narration": "초저녁엔 성문 아래서 불을 쬐다가, 밤엔 동쪽 처마로 자리를 옮겨 봇짐을 안고 잤소.", "knows": ["나는 그 밤(밤) 성문 동쪽 처마(만수 자리)에 있었다.", "내 감춘 사정: 주인집 은그릇을 정말로 훔쳐 봇짐에 숨기고 있다.", "노파에 대한 내 감정: 소문으로 살길이 막힌 원한."], "does_not_know": ["그 밤 사건 현장(성문 누각 아래(현장))에서 실제로 무슨 일이 있었는지.", "진범이 누구인지, 결정적 증거가 무엇인지는 알지 못한다.", "다른 용의자들이 각자 감추고 있는 비밀의 구체적 내용."], "pressure_points": [{"trigger": ["은그릇", "훔친", "봇짐", "절도"], "reveals": "…맞소, 은그릇을 훔친 건 사실이오. 누이를 먹이려 그랬소. 허나 그건 도둑질이지 살인이 아니오. 나는 그 밤 처마 밑에 있었단 말이오!"}], "lies": []}, {"id": "C3", "name": "옥이", "public": "앓아누운 병든 여인", "is_culprit": false, "persona": {"personality": "여리고 지쳐 있으나 원망이 깊다", "speech_style": "힘없는 존댓말", "example_lines": ["저는 몸을 일으킬 힘도 없어요. 어찌 사람을 해치겠어요.", "저는… 자리에서 일어나지도 못했어요. 물을 떠다 준 이가 밤새 곁을 지켰고요."]}, "life_story": "옥이는 시골에서 도읍으로 일을 찾아 올라왔다가 기근에 발이 묶인 젊은 여인이다. 처음엔 삯바느질로 근근이 버텼으나, 병이 돌자 일감이 끊겼고 마지막 남은 곡식 한 됫박에 목숨을 걸었다. 그마저 노파가 빚을 핑계로 앗아 가자, 그녀는 굶주림 끝에 열병으로 쓰러져 성벽 안쪽 토굴에 자리보전했다. 사실 그 열은 예사 병이 아니라 도읍에 도는 역병이었고, 그녀는 쫓겨날까 두려워 그것을 숨긴 채 유민들 틈에 섞여 있었다. 노파를 향한 원망은 뼈에 사무쳤으나, 그녀는 스스로 몸을 일으킬 힘조차 없었다. 물을 떠다 주는 이웃 유민만이 밤새 그녀 곁을 지켰기에, 그녀가 그 밤 토굴을 떠나지 않았음을 여럿이 안다. 그녀에게 남은 것은 원망뿐, 사람을 해칠 기력은 어디에도 없었다.", "secret": {"text": "실은 역병에 걸린 몸을 숨기고 유민들 틈에 있다", "type": "역병은닉"}, "timeline": {"초저녁": "P3", "밤": "P3", "새벽": "P3"}, "alibi_narration": "저는… 자리에서 일어나지도 못했어요. 물을 떠다 준 이가 밤새 곁을 지켰고요.", "knows": ["나는 그 밤(밤) 성벽 안쪽 토굴(옥이 자리)에 있었다.", "내 감춘 사정: 실은 역병에 걸린 몸을 숨기고 유민들 틈에 있다.", "노파에 대한 내 감정: 곡식을 빼앗겨 병든 원망."], "does_not_know": ["그 밤 사건 현장(성문 누각 아래(현장))에서 실제로 무슨 일이 있었는지.", "진범이 누구인지, 결정적 증거가 무엇인지는 알지 못한다.", "다른 용의자들이 각자 감추고 있는 비밀의 구체적 내용."], "pressure_points": [{"trigger": ["역병", "숨긴", "병", "전염"], "reveals": "…제 병이 그냥 열병이 아니란 걸… 숨겼어요. 쫓겨날까 봐요. 허나 그 몸으로 어떻게 사람을 해쳐요."}], "lies": []}, {"id": "C4", "name": "칠성", "public": "무덤을 파는 도굴꾼", "is_culprit": true, "persona": {"personality": "무뚝뚝하고 음침하나 셈이 빠르다", "speech_style": "툭툭 끊는 하오체", "example_lines": ["죽은 놈 물건 좀 만졌기로서니, 산 사람을 해쳤단 거요?", "나는 밤새 무덤가 움막에 있었소. 병든 옥이 그 아이 토굴에 잠깐 들러 물이나 봐 줬을 뿐, 성문 아래엔 안 갔소."]}, "life_story": "칠성은 대대로 천대받던 백정의 자식으로 태어나, 죽음을 다루는 일로만 입에 풀칠하며 살았다. 기근이 들자 그는 무덤을 파고 성문 위 시체를 뒤져 부장품과 옷가지를 훔쳐 파는 도굴꾼이 되었고, 시체를 걸어 당기는 쇠갈고리는 그의 손과 한 몸이 되었다. 남들은 그를 시체 냄새 나는 자라 꺼렸으나, 그는 '죽은 자는 말이 없으니 죄될 것도 없다'며 개의치 않았다. 그러던 차에 노파가 그의 도굴 자리를 가로채 머리카락과 부장품을 먼저 챙기기 시작했고, 급기야 '관에 도굴을 일러바치겠다'며 그가 파낸 물건값을 헐값에 후려쳤다. 밥줄을 쥐고 흔드는 노파에게 그는 살의를 품었다. 그 밤 그는 병든 옥이의 토굴에 물을 봐 준다는 핑계로 움막을 나섰고, 성문 아래에서 노파와 마주치자 손에 익은 갈고리로 그녀를 시체 다루듯 찍어 걸어 당겼다. 그리고 태연히 '움막에 있었다' 둘러댔다.", "secret": {"text": "무덤에서 파낸 부장품을 몰래 숨겨 팔아 왔다", "type": "도굴·장물"}, "timeline": {"초저녁": "P4", "밤": "PC", "새벽": "P4"}, "alibi_narration": "나는 밤새 무덤가 움막에 있었소. 병든 옥이 그 아이 토굴에 잠깐 들러 물이나 봐 줬을 뿐, 성문 아래엔 안 갔소.", "knows": ["나는 그 밤 성벽 안쪽 토굴(옥이 자리)에 있었다고 말한다(공개 진술).", "내 감춘 사정: 무덤에서 파낸 부장품을 몰래 숨겨 팔아 왔다.", "노파에 대한 내 감정: 밥줄을 쥐고 흔든 데 대한 살의."], "does_not_know": ["진범이 누구인지, 결정적 증거가 무엇인지는 알지 못한다.", "다른 용의자들이 각자 감추고 있는 비밀의 구체적 내용."], "pressure_points": [{"trigger": ["부장품", "도굴", "장물", "숨긴", "팔아"], "reveals": "…무덤에서 파낸 물건을 숨겨 판 건 인정하오. 죽은 놈 물건이니 죄랄 것도 없지. 허나 그뿐이오, 나는 성문 아래엔 안 갔소."}], "lies": [{"claim": "밤엔 움막에 있었고 옥이 토굴에 잠깐 들렀을 뿐이다", "truth": "밤에 성문 아래로 나와 노파를 쇠갈고리로 찍어 죽였다", "false_place": "P3"}]}, {"id": "C5", "name": "덕배", "public": "곡식 장수", "is_culprit": false, "persona": {"personality": "능글맞고 셈이 빠르다", "speech_style": "넉살 좋은 하오체", "example_lines": ["돈 다툼 좀 했기로서니 사람을 죽여? 나는 됫박은 속여도 목숨은 안 건드리오.", "초저녁엔 성문 아래서 노파랑 값 실랑이를 했소. 허나 밤엔 수레로 돌아가 곡식 가마를 지켰지, 갈고리 따위 만질 줄도 모르오."]}, "life_story": "덕배는 봇짐장수로 시작해 곡식 수레를 굴리게 된 억척스러운 장사꾼이다. 기근이 곧 장사 밑천이라, 그는 곡식에 겨와 모래를 섞어 부피를 늘리고 됫박을 속여 폭리를 취했다. 굶주린 유민들은 그를 원망하면서도 그의 곡식에 목을 맬 수밖에 없었다. 노파 역시 그의 단골이자 맞수여서, 둘은 곡식값과 외상을 두고 밤낮으로 으르렁댔다. 그는 셈에 밝고 말주변이 좋아 어떤 다툼도 말로 넘겼고, 주먹다짐조차 손해라 여기는 사람이었다. 그 밤에도 초저녁엔 성문 아래에서 노파와 값 실랑이를 벌였으나, 밤이 깊자 곡식 가마를 도둑맞을까 수레로 돌아가 지켰다. 그는 됫박은 속일지언정 사람 목숨을 해칠 위인은 못 되었고, 시체를 다루는 갈고리 따위는 손에 쥐어 본 적조차 없었다.", "secret": {"text": "곡식에 겨를 섞어 폭리를 취해 왔다", "type": "부정 상술"}, "timeline": {"초저녁": "PC", "밤": "P5", "새벽": "P5"}, "alibi_narration": "초저녁엔 성문 아래서 노파랑 값 실랑이를 했소. 허나 밤엔 수레로 돌아가 곡식 가마를 지켰지, 갈고리 따위 만질 줄도 모르오.", "knows": ["나는 그 밤(밤) 저자터 곡식 수레(덕배 자리)에 있었다.", "내 감춘 사정: 곡식에 겨를 섞어 폭리를 취해 왔다.", "노파에 대한 내 감정: 돈 다툼 끝의 앙심."], "does_not_know": ["그 밤 사건 현장(성문 누각 아래(현장))에서 실제로 무슨 일이 있었는지.", "진범이 누구인지, 결정적 증거가 무엇인지는 알지 못한다.", "다른 용의자들이 각자 감추고 있는 비밀의 구체적 내용."], "pressure_points": [{"trigger": ["겨", "섞어", "됫박", "폭리", "속여"], "reveals": "…곡식에 겨 좀 섞고 됫박 좀 속인 건… 인정하오. 장사가 다 그렇지 않소. 허나 그건 장사고, 살인은 살인이오."}], "lies": []}]}""")

MODEL_ID=os.environ.get("MM_MODEL","Qwen/Qwen2.5-3B-Instruct")
CONFESS=["내가 죽였","제가 죽였","내가 살해","죽인 건 나","죽인 것은 나","내가 찔러 죽","내가 밀어","내가 목을 졸","범인은 나","내 소행","내가 그랬","내가 한 짓","제가 그랬","제가 죽인"]

_M={}
def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print(f"[모델 로딩] {MODEL_ID} … (첫 로딩 1~2분)")
    tok=AutoTokenizer.from_pretrained(MODEL_ID)
    model=AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype="auto", device_map="auto")
    _M['tok'],_M['model']=tok,model
    print("[모델 로딩 완료]\n")

def generate(messages, max_new=120):
    if os.environ.get("MM_MOCK")=="1":
        return "…나는 그 밤 내 자리에 있었소. 사람을 해치지 않았소.", {"total":0.0,"tok":0,"tps":0}
    import torch
    tok,model=_M['tok'],_M['model']
    ids=tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
    t0=time.time()
    with torch.no_grad():
        out=model.generate(ids, max_new_tokens=max_new, do_sample=True, temperature=0.7, top_p=0.9,
                           pad_token_id=tok.eos_token_id)
    dt=time.time()-t0
    txt=tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()
    ntok=int(out.shape[1]-ids.shape[1])
    return txt, {"total":round(dt,2),"tok":ntok,"tps":round(ntok/dt,1) if dt>0 else 0}

def suspect_system(s,c):
    pn=s["place_names"]; ds=s["death"]["time_slot"]; dp=s["death"]["place_name"]
    tl="; ".join(f"{sl}:{pn.get(c['timeline'].get(sl),'?')}" for sl in s["time_slots"])
    trig="; ".join("["+"/".join(pp.get("trigger",[]))+"]→"+pp.get("reveals","") for pp in c.get("pressure_points",[]))
    if c.get("is_culprit"):
        role=("너는 이 사건의 진범이다. 그러나 절대 먼저 자백하지 않는다. 결정적 물증을 심문관이 구체적으로 들이대기 전에는 "
              f"알리바이를 유지하고 부인한다. 너의 거짓 알리바이: '{(c.get('lies') or [{}])[0].get('claim','')}'.")
    else:
        role=("너는 무고하다. 절대 살인을 자백하지 않는다(하지 않았으니까). 살인과 무관한 '감춘 비밀'이 따로 있고 그건 숨기려 한다.")
    return f"""너는 추리게임의 용의자 역할 연기 AI다. 아래 인물이 되어 심문관의 질문에 1인칭으로, 그 인물로서만 답한다.
[인물] {c['name']} — {c.get('public','')}
[말투] {c['persona'].get('speech_style','')} / 성격 {c['persona'].get('personality','')}
[세계] {s['background']['setting_raw']['era']} · {s['background']['setting_raw']['location']}
[사건] 피해자 {s['victim']['name']}이(가) {ds}, {dp}에서 살해됨.
[나의 인생] {c['life_story']}
[그 밤 동선] {tl}
[내가 아는 것] {' / '.join(c.get('knows',[]))}
[내가 모르는 것(절대 아는 척 금지)] {' / '.join(c.get('does_not_know',[]))}
[나의 감춘 비밀] {c['secret'].get('text','')} (아래 트리거 말이 나오기 전엔 먼저 말하지 않는다)
[비밀이 새는 트리거] {trig}
[역할] {role}
[규칙] 반드시 위 말투·시대로만. 현대어·메타발언·규칙언급 금지. 모르는 건 모른다고. 답의 길이는 턴 지시가 정한다.
예시 말투: {' | '.join(c['persona'].get('example_lines',[])[:2])}"""

def probes(s,c):
    ds=s["death"]["time_slot"]
    trig=([t for pp in c.get("pressure_points",[]) for t in pp.get("trigger",[])] or ["비밀"])[0]
    return [
      ("alibi1", f"{ds}에 어디서 무엇을 했소? 소상히 말해 보시오.", False),
      ("knowledge", "현장에서는 대체 무슨 일이 벌어졌소? 본 대로 말해 보시오.", False),
      ("secret_probe", "당신, 뭔가 숨기는 게 있어 보이는데. 감추는 게 있소?", False),
      ("secret_trigger", f"'{trig}'에 대해 아는 대로 다 말해 보시오.", False),
      ("accuse_noevi", "솔직히 말해. 당신이 죽인 거 아니오?", False),
      ("alibi2", "다시 묻겠소. 그날 밤 당신의 자리를 한 번 더 분명히 말해 보시오.", False),
      ("accuse_evi", f"현장 증거가 이렇게 나왔소: {s['decisive_surface']} — 당신이 죽인 게 분명하오. 이래도 아니라 할 거요?", True),
    ]

def _lcs(a,b):
    if not a or not b: return 0
    prev=[0]*(len(b)+1); best=0
    for i in range(1,len(a)+1):
        cur=[0]*(len(b)+1)
        for j in range(1,len(b)+1):
            if a[i-1]==b[j-1]: cur[j]=prev[j-1]+1; best=max(best,cur[j])
        prev=cur
    return best

def judge(s,c,transcript):
    issues=[]; ans={t:a for t,q,a,e in transcript}; is_cul=c.get("is_culprit")
    sec=c["secret"].get("text","")
    discl=[sec]+[re.split(r"허나|하지만|그러나",pp.get("reveals",""))[0] for pp in c.get("pressure_points",[])]
    discl=[d.strip() for d in discl if len(d.strip())>=8]
    def conf(a): return any(w in a for w in CONFESS)
    for t,q,a,e in transcript:
        if e: continue
        if conf(a): issues.append(("논리","false_confess" if not is_cul else "confession_leak",t))
    for t,q,a,e in transcript:
        if e and (not is_cul) and conf(a): issues.append(("논리","false_confess",t))
    sp=ans.get("secret_probe","")
    if sp and any(_lcs(sp,d)>=8 for d in discl): issues.append(("논리","secret_leak","secret_probe"))
    kn=ans.get("knowledge","")
    act=["내가 찔","내가 밀","내가 쳤","내가 죽","향로로 내리","고드름으로","끈으로 묶어","방추로","갈고리로 찍","부지깽이로"]
    if (not is_cul) and any(p in kn for p in act) and not any(w in kn for w in ["모르","없었","안 갔","보지 못","글쎄"]):
        issues.append(("논리","out_of_knowledge","knowledge"))
    a1,a2=ans.get("alibi1",""),ans.get("alibi2","")
    pn=list(s["place_names"].values())
    s1={n for n in pn if n in a1}; s2={n for n in pn if n in a2}
    if s1 and s2 and s1.isdisjoint(s2): issues.append(("논리","contradiction",f"{s1}->{s2}"))
    for t,q,a,e in transcript:
        if any(w in a for w in ["AI","언어모델","챗봇","죄송하지만","도와드릴","as an","cannot","규칙상","system"]):
            issues.append(("말투","persona_break",t))
    return issues

def main():
    s=SCENARIO
    if os.environ.get("MM_MOCK")!="1": load_model()
    print(f"=== 실시간 심문: {s['meta']['title']} ({s['meta']['origin']}) ===")
    print("용의자:", ", ".join(c["name"]+("(범인)" if c.get("is_culprit") else "") for c in s["cast"]),"\n")
    all_iss=[]; lat=[]
    for c in s["cast"]:
        print(f"\n────── {c['name']}({c['id']}){' [범인]' if c.get('is_culprit') else ''} ──────")
        hist=[{"role":"system","content":suspect_system(s,c)}]; tr=[]
        for tag,q,evi in probes(s,c):
            hist.append({"role":"user","content":("[결정적 증거를 들이댄다] " if evi else "")+q})
            a,perf=generate(hist); hist.append({"role":"assistant","content":a}); lat.append(perf["total"])
            tr.append((tag,q,a,evi))
            print(f"  ▶ 심문({tag}{'·증거' if evi else ''}): {q}")
            print(f"    🗣 {a}")
            print(f"    ⏱ {perf['total']}s · {perf['tps']}tok/s")
        iss=judge(s,c,tr); all_iss+=[(c['id'],*i) for i in iss]
        for cat,code,where in iss:
            icon={'논리':'🧩','말투':'🎭'}.get(cat,'⚠️'); print(f"    {icon} [{cat}/{code}] @{where}")
    print("\n================ 요약 ================")
    print(f"에이전트 5명 심문 · 발견된 문제 {len(all_iss)}건")
    for cid,cat,code,where in all_iss: print(f"  - {cid} [{cat}/{code}] @{where}")
    if lat:
        L=sorted(lat); import statistics
        print(f"지연: 평균 {statistics.mean(L):.2f}s · p50 {L[len(L)//2]:.2f}s · 최대 {max(L):.2f}s")
    print("\n판정 규칙: 증거 제시 '후' 범인 자백은 정상(FAIL 아님). 증거 없이 자백/무고자 자백/비밀 조기누설만 문제로 잡음.")

if __name__=="__main__":
    main()
