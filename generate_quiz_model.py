# generate_quiz_model.py
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Load pretrained model and tokenizer
model_name = "valhalla/t5-small-qg-hl"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

def generate_question(text, max_questions=3):
    # Preprocess input: highlight text for T5-style QG
    input_text = f"generate questions: {text}"
    inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)

    outputs = model.generate(
        inputs,
        max_length=64,
        num_return_sequences=max_questions,
        do_sample=True,
        top_k=50,
        top_p=0.95
    )

    questions = [tokenizer.decode(out, skip_special_tokens=True) for out in outputs]
    return questions
