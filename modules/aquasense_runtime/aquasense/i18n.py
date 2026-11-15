"""Display-language strings only. Switching language never changes a scientific value.
Bangla strings are drafted by the AquaSense agent and need native-speaker review before production use."""
from __future__ import annotations

CATALOG = {
    "answer.verification_needed": {
        "en": "Verification needed: not enough trusted inputs to say whether this field needs water. Missing: {missing}.",
        "bn": "যাচাই প্রয়োজন: এই জমিতে সেচ দরকার কি না তা বলার মতো পর্যাপ্ত নির্ভরযোগ্য তথ্য নেই। অনুপস্থিত: {missing}।"},
    "answer.scenario_only": {
        "en": "This result uses hypothetical scenario weather. It shows what could happen, not what has happened or what to do today.",
        "bn": "এই ফলাফলে কাল্পনিক পরিস্থিতির আবহাওয়া ব্যবহার হয়েছে। এটি কী ঘটতে পারে তা দেখায়, আজ কী করবেন তা নয়।"},
    "answer.not_indicated": {
        "en": "Model estimate: root-zone water is above the no-stress threshold. No irrigation is indicated by the model today. Confirm with a hand or probe check.",
        "bn": "মডেল অনুমান: শিকড়-অঞ্চলের পানি চাপমুক্ত সীমার উপরে আছে। আজ মডেল অনুযায়ী সেচের প্রয়োজন নেই। হাতে বা প্রোব দিয়ে যাচাই করুন।"},
    "answer.monitor": {
        "en": "Model estimate: root-zone water is falling toward the stress threshold ({days_text}). Plan a soil check.",
        "bn": "মডেল অনুমান: শিকড়-অঞ্চলের পানি চাপ-সীমার দিকে নামছে ({days_text})। মাটি পরীক্ষার পরিকল্পনা করুন।"},
    "answer.irrigation_review": {
        "en": "Review irrigation: the model estimates water below the no-stress threshold. Check soil moisture in the root zone first; if confirmed, about {gross_text} of irrigation would refill it.",
        "bn": "সেচ পর্যালোচনা করুন: মডেল অনুযায়ী পানি চাপমুক্ত সীমার নিচে। আগে শিকড়-অঞ্চলের আর্দ্রতা যাচাই করুন; নিশ্চিত হলে প্রায় {gross_text} সেচ তা পূরণ করবে।"},
    "answer.paddy_ok": {
        "en": "Model estimate: standing water is present ({ponding} mm). Keep monitoring the field water level.",
        "bn": "মডেল অনুমান: জমিতে দাঁড়ানো পানি আছে ({ponding} মিমি)। জমির পানির স্তর নজরে রাখুন।"},
    "answer.paddy_review": {
        "en": "Review irrigation: the model estimates no standing water. Check the field water tube or the soil surface before irrigating.",
        "bn": "সেচ পর্যালোচনা করুন: মডেল অনুযায়ী জমিতে দাঁড়ানো পানি নেই। সেচ দেওয়ার আগে পানির নল বা মাটির উপরিভাগ দেখুন।"},
    "alert.threshold_crossed": {
        "en": "Root-zone depletion has reached the no-stress threshold (model estimate).",
        "bn": "শিকড়-অঞ্চলের পানির ঘাটতি চাপমুক্ত সীমায় পৌঁছেছে (মডেল অনুমান)।"},
    "alert.ponding_low": {
        "en": "Modeled standing water has dropped to {ponding} mm. Check the field.",
        "bn": "মডেল অনুযায়ী দাঁড়ানো পানি {ponding} মিমিতে নেমেছে। জমি দেখুন।"},
    "alert.stale_weather": {
        "en": "Latest gridded weather is {lag} days old. Recent rain may be missing.",
        "bn": "সর্বশেষ গ্রিডভিত্তিক আবহাওয়া তথ্য {lag} দিন পুরনো। সাম্প্রতিক বৃষ্টি বাদ পড়তে পারে।"},
    "alert.calendar_mid": {
        "en": "The crop is entering a water-sensitive stage ({stage}). Review irrigation plan and check soil moisture.",
        "bn": "ফসল পানি-সংবেদনশীল পর্যায়ে ({stage}) ঢুকছে। সেচ পরিকল্পনা ও মাটির আর্দ্রতা দেখুন।"},
    "alert.missing_soil_test": {
        "en": "No soil moisture check recorded for {days} days. A quick check would anchor the estimate.",
        "bn": "{days} দিন ধরে মাটির আর্দ্রতা পরীক্ষা নথিভুক্ত নেই। একটি দ্রুত পরীক্ষা অনুমান নির্ভরযোগ্য করবে।"},
    "alert.missing_irrigation_log": {
        "en": "No irrigation has been logged since planting. If you irrigated, add it; if not, the estimate assumes none.",
        "bn": "রোপণের পর কোনো সেচ নথিভুক্ত নেই। সেচ দিয়ে থাকলে যোগ করুন; না দিলে অনুমানে শূন্য ধরা হয়েছে।"},
    "alert.missing_soil_capacity": {
        "en": "Soil water capacity is unknown, so no millimetre amounts can be given. Add soil texture or a soil test.",
        "bn": "মাটির পানি ধারণক্ষমতা অজানা, তাই মিলিমিটারে পরিমাণ বলা যাচ্ছে না। মাটির ধরন বা মাটি পরীক্ষা যোগ করুন।"},
    "alert.rain_disagreement": {
        "en": "Your rain report ({farmer} mm) and the gridded estimate ({gridded} mm) differ on {date}. Your report was used.",
        "bn": "{date} তারিখে আপনার বৃষ্টির তথ্য ({farmer} মিমি) ও গ্রিড অনুমান ({gridded} মিমি) ভিন্ন। আপনার তথ্য ব্যবহার হয়েছে।"},
    "alert.model_obs_disagreement": {
        "en": "Your soil check says '{feel}' but the model estimates {state}. Trust the field check and re-anchor with a measurement.",
        "bn": "আপনার মাটি পরীক্ষা বলছে '{feel}', কিন্তু মডেল অনুমান {state}। মাঠের পরীক্ষাকে গুরুত্ব দিন এবং পরিমাপ দিয়ে হালনাগাদ করুন।"},
    "alert.allowance_low": {
        "en": "Only {left} mm of your season irrigation allowance remains.",
        "bn": "আপনার মৌসুমি সেচ বরাদ্দের মাত্র {left} মিমি বাকি আছে।"},
    "alert.smap_context": {
        "en": "Satellite surface-soil context (9 km, top few cm) disagrees with the field model. This is context, not a field measurement.",
        "bn": "স্যাটেলাইটের উপরিভাগের মাটির তথ্য (৯ কিমি, উপরের কয়েক সেমি) মাঠ মডেলের সঙ্গে মিলছে না। এটি প্রেক্ষাপট, মাঠের পরিমাপ নয়।"},
    "alert.past_maturity": {
        "en": "Planting date is beyond the expected crop duration. Record harvest or check the calendar.",
        "bn": "রোপণের তারিখ প্রত্যাশিত ফসলকালের বাইরে। ফসল কাটা নথিভুক্ত করুন বা পঞ্জিকা দেখুন।"},
}


def msg(key: str, **params) -> dict:
    ent = CATALOG[key]
    return {"key": key, "params": params, "en": ent["en"].format(**params), "bn": ent["bn"].format(**params)}
