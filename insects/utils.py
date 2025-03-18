from googletrans import Translator

def translate_text(text, dest_lang="vi"):
    translator = Translator()
    try:
        translation = translator.translate(text, dest=dest_lang)
        return translation.text
    except Exception as e:
        return f"Translation error: {e}"
