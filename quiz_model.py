# quiz_model.py
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import torch
import re
import random

# Load the question generation model
qg_tokenizer = AutoTokenizer.from_pretrained("valhalla/t5-base-e2e-qg")
qg_model = AutoModelForSeq2SeqLM.from_pretrained("valhalla/t5-base-e2e-qg")
question_generator = pipeline("text2text-generation", model=qg_model, tokenizer=qg_tokenizer)

# Load the QA model to extract accurate answers
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

def generate_quiz(content_text, num_questions=15):
    questions = []
    seen = set()

    sentences = [s.strip() for s in content_text.strip().split('.') if s.strip()]
    chunks = [f"{sentences[i]}. {sentences[i+1]}." for i in range(len(sentences) - 1)]

    for i, chunk in enumerate(chunks):
        if len(questions) >= num_questions:
            break

        input_text = f"generate question: {chunk}"
        try:
            result = question_generator(input_text, max_new_tokens=64, num_return_sequences=1, num_beams=4)[0]
            question_text = result['generated_text'].strip()
        except Exception:
            continue

        question_text = question_text.replace("<sep>", " ")
        potential_questions = re.split(r'\?[\s\.]*', question_text)

        for q in potential_questions:
            q = q.strip()
            if q and len(questions) < num_questions:
                clean_q = q + "?"
                if clean_q not in seen:
                    seen.add(clean_q)

                    # Use QA model to get accurate answer from context
                    try:
                        qa_result = qa_pipeline({"context": chunk, "question": clean_q})
                        answer = qa_result["answer"].strip()
                    except Exception:
                        answer = "Unknown"

                    options = generate_options(answer, chunk)
                    random.shuffle(options)

                    questions.append({
                        "question": clean_q,
                        "options": options,
                        "answer": answer
                    })

    return {"questions": questions}

def generate_options(correct, context):
    distractors = set()
    distractors.add(correct)
    words = [w.strip('.,') for w in context.split() if len(w) > 4 and w.lower() != correct.lower()]

    while len(distractors) < 4 and words:
        candidate = random.choice(words)
        distractors.add(candidate)

    return list(distractors)[:4]




