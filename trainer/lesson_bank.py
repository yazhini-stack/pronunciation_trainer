"""Built-in lesson bank providing structured words and phrases across languages and categories."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import random
from trainer.logger import app_logger, LessonDataError


@dataclass
class LessonItem:
    """Represents a single word or phrase practice item."""
    id: str
    language: str
    language_name: str
    category: str
    level: str  # beginner, intermediate, advanced
    item_type: str  # word, phrase
    target_text: str
    romanization: str
    translation: str
    phonetic_guide: str
    tips: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


# Comprehensive multi-language lesson repository
LESSON_DATA: List[LessonItem] = [
    # ---------------- SPANISH (es) ----------------
    # Greetings
    LessonItem("es_gret_01", "es", "Spanish", "greetings", "beginner", "word", "Hola", "Hola", "Hello", "OH-lah", "The 'H' is completely silent in Spanish."),
    LessonItem("es_gret_02", "es", "Spanish", "greetings", "beginner", "phrase", "Buenos días", "Buenos días", "Good morning", "BWEH-nohs DEE-ahs", "Stress the 'dí' in días."),
    LessonItem("es_gret_03", "es", "Spanish", "greetings", "beginner", "phrase", "Buenas tardes", "Buenas tardes", "Good afternoon", "BWEH-nahs TAHR-dehs", "Keep 'd' soft between vowels."),
    LessonItem("es_gret_04", "es", "Spanish", "greetings", "intermediate", "phrase", "¿Cómo estás?", "¿Cómo estás?", "How are you?", "KOH-moh ehs-TAHS", "Raise pitch slightly at the end for questions."),
    LessonItem("es_gret_05", "es", "Spanish", "greetings", "beginner", "word", "Gracias", "Gracias", "Thank you", "GRAH-syahs", "Soft tap on 'r' with the tip of the tongue."),
    LessonItem("es_gret_06", "es", "Spanish", "greetings", "intermediate", "phrase", "Mucho gusto", "Mucho gusto", "Nice to meet you", "MOO-choh GOOS-toh", "Short crisp vowels, no drawn-out diphthongs."),
    
    # Numbers
    LessonItem("es_num_01", "es", "Spanish", "numbers", "beginner", "word", "Uno", "Uno", "One", "OO-noh", "Clear 'u' like the oo in food."),
    LessonItem("es_num_02", "es", "Spanish", "numbers", "beginner", "word", "Cinco", "Cinco", "Five", "SEEN-koh", "Latin American uses 's' sound; Spain uses 'th'."),
    LessonItem("es_num_03", "es", "Spanish", "numbers", "beginner", "word", "Diez", "Diez", "Ten", "DYEHS", "One syllable glide from 'i' to 'e'."),
    LessonItem("es_num_04", "es", "Spanish", "numbers", "intermediate", "word", "Veinte", "Veinte", "Twenty", "BAYN-teh", "The 'v' is pronounced like a soft 'b'."),
    LessonItem("es_num_05", "es", "Spanish", "numbers", "intermediate", "word", "Cincuenta", "Cincuenta", "Fifty", "seen-KWEHN-tah", "Clear transition from 'cu' to 'en'."),

    # Travel
    LessonItem("es_trv_01", "es", "Spanish", "travel", "beginner", "word", "Aeropuerto", "Aeropuerto", "Airport", "ah-eh-roh-PWEHR-toh", "Distinct syllables for 'a-e'."),
    LessonItem("es_trv_02", "es", "Spanish", "travel", "intermediate", "phrase", "¿Dónde está el hotel?", "¿Dónde está el hotel?", "Where is the hotel?", "DOHN-deh ehs-TAH ehl oh-TEHL", "Remember the 'h' in hotel is silent."),
    LessonItem("es_trv_03", "es", "Spanish", "travel", "intermediate", "phrase", "Un billete de tren", "Un billete de tren", "A train ticket", "oon bee-YEH-teh deh trehn", "Double 'll' sounds like 'y' in yellow."),
    LessonItem("es_trv_04", "es", "Spanish", "travel", "advanced", "phrase", "Quisiera cambiar dinero", "Quisiera cambiar dinero", "I would like to exchange money", "kee-SYEH-rah kahm-BYAHR dee-NEH-roh", "Stress 'bie' and tap the 'r'."),

    # Food
    LessonItem("es_foo_01", "es", "Spanish", "food", "beginner", "word", "Agua", "Agua", "Water", "AH-gwah", "Gentle 'g' glide."),
    LessonItem("es_foo_02", "es", "Spanish", "food", "beginner", "word", "Café", "Café", "Coffee", "kah-FEH", "Strong stress on the accented 'é'."),
    LessonItem("es_foo_03", "es", "Spanish", "food", "intermediate", "phrase", "La cuenta por favor", "La cuenta por favor", "The bill please", "lah KWEHN-tah pohr fah-VOHR", "Glide 'fa-VOR' with stress on final syllable."),
    LessonItem("es_foo_04", "es", "Spanish", "food", "intermediate", "phrase", "Una mesa para dos", "Una mesa para dos", "A table for two", "OO-nah MEH-sah PAH-rah dohs", "Light single flap on 'para'."),

    # Business
    LessonItem("es_bus_01", "es", "Spanish", "business", "intermediate", "word", "Reunión", "Reunión", "Meeting", "rreh-oo-NYOHN", "Trill the initial 'r' firmly."),
    LessonItem("es_bus_02", "es", "Spanish", "business", "intermediate", "word", "Contrato", "Contrato", "Contract", "kohn-TRAH-toh", "Crisp 't' sounds without heavy aspiration."),
    LessonItem("es_bus_03", "es", "Spanish", "business", "advanced", "phrase", "Tenemos una propuesta", "Tenemos una propuesta", "We have a proposal", "teh-NEH-mohs OO-nah proh-PWEHS-tah", "Clear rhythmic cadence."),
    LessonItem("es_bus_04", "es", "Spanish", "business", "advanced", "phrase", "El presupuesto trimestral", "El presupuesto trimestral", "The quarterly budget", "ehl preh-soo-PWEHS-toh tree-mehs-TRAHL", "Final stress on 'tral'."),

    # ---------------- FRENCH (fr) ----------------
    # Greetings
    LessonItem("fr_gret_01", "fr", "French", "greetings", "beginner", "word", "Bonjour", "Bonjour", "Hello / Good day", "bohn-ZHOOR", "Nasal 'on' followed by soft voiced 'zh' sound."),
    LessonItem("fr_gret_02", "fr", "French", "greetings", "beginner", "phrase", "Bonsoir", "Bonsoir", "Good evening", "bohn-SWAHR", "Nasal 'on' and uvular French 'r'."),
    LessonItem("fr_gret_03", "fr", "French", "greetings", "intermediate", "phrase", "Comment allez-vous ?", "Comment allez-vous ?", "How are you? (formal)", "koh-mahn tah-lay VOO", "Perform liaison between 'Comment' and 'allez'."),
    LessonItem("fr_gret_04", "fr", "French", "greetings", "beginner", "word", "Merci", "Merci", "Thank you", "mehr-SEE", "Stress falls gently on the second syllable."),
    LessonItem("fr_gret_05", "fr", "French", "greetings", "intermediate", "phrase", "Au revoir", "Au revoir", "Goodbye", "oh ruh-VWAHR", "Glide into the 'vwar' smoothly."),

    # Numbers
    LessonItem("fr_num_01", "fr", "French", "numbers", "beginner", "word", "Un", "Un", "One", "uhn", "Short nasal vowel produced through the nose."),
    LessonItem("fr_num_02", "fr", "French", "numbers", "beginner", "word", "Trois", "Trois", "Three", "trwah", "Guttural French 'r' followed by 'wah'."),
    LessonItem("fr_num_03", "fr", "French", "numbers", "beginner", "word", "Sept", "Sept", "Seven", "seht", "The 'p' is silent; pronounce crisp 't'."),
    LessonItem("fr_num_04", "fr", "French", "numbers", "intermediate", "word", "Vingt", "Vingt", "Twenty", "vahn", "Silent 'g' and 't' at the end."),
    LessonItem("fr_num_05", "fr", "French", "numbers", "intermediate", "word", "Quarante", "Quarante", "Forty", "kah-RAHNT", "Crisp ending, nasal 'an'."),

    # Travel
    LessonItem("fr_trv_01", "fr", "French", "travel", "beginner", "word", "Gare", "Gare", "Train station", "gahr", "Open 'ah' sound with uvular 'r'."),
    LessonItem("fr_trv_02", "fr", "French", "travel", "intermediate", "phrase", "Où est la station de métro ?", "Où est la station de métro ?", "Where is the subway station?", "oo eh lah stah-SYOHN duh meh-TROH", "High nasal on 'tion'."),
    LessonItem("fr_trv_03", "fr", "French", "travel", "advanced", "phrase", "Un passeport s'il vous plaît", "Un passeport s'il vous plaît", "A passport please", "uhn pahs-POHR seel voo pleh", "Final 't' of passeport is silent."),

    # Food
    LessonItem("fr_foo_01", "fr", "French", "food", "beginner", "word", "Croissant", "Croissant", "Croissant", "krwah-SAHN", "French 'r', nasal ending, final 't' silent."),
    LessonItem("fr_foo_02", "fr", "French", "food", "beginner", "word", "Fromage", "Fromage", "Cheese", "froh-MAHZH", "Soft 'zh' sound at the end, like measure."),
    LessonItem("fr_foo_03", "fr", "French", "food", "intermediate", "phrase", "L'addition s'il vous plaît", "L'addition s'il vous plaît", "The bill please", "lah-dee-SYOHN seel voo pleh", "Clear syllables with nasal 'on'."),
    LessonItem("fr_foo_04", "fr", "French", "food", "intermediate", "phrase", "De l'eau minérale", "De l'eau minérale", "Mineral water", "duh LOH mee-neh-RAHL", "Smooth liaison from 'l' into 'eau'."),

    # Business
    LessonItem("fr_bus_01", "fr", "French", "business", "intermediate", "word", "Entreprise", "Entreprise", "Company / Enterprise", "ahn-truh-PREEZ", "First syllable is nasal 'en'."),
    LessonItem("fr_bus_02", "fr", "French", "business", "advanced", "phrase", "Ordre du jour", "Ordre du jour", "Agenda", "OHR-druh dyoo ZHOOR", "The 'u' in 'du' requires rounded lips."),
    LessonItem("fr_bus_03", "fr", "French", "business", "advanced", "phrase", "Nous avons un accord", "Nous avons un accord", "We have an agreement", "nooz ah-VOHN uhn ah-KOHR", "Liaison 'nous-z-avons'."),

    # ---------------- HINDI (hi) ----------------
    # Greetings
    LessonItem("hi_gret_01", "hi", "Hindi", "greetings", "beginner", "word", "नमस्ते", "Namaste", "Hello / Greetings", "nuh-muh-STAY", "Stress the final syllable 'stay' with hands together."),
    LessonItem("hi_gret_02", "hi", "Hindi", "greetings", "beginner", "phrase", "आप कैसे हैं?", "Aap kaise hain?", "How are you? (polite)", "ahp KY-say hain", "Nasal resonance on 'hain'."),
    LessonItem("hi_gret_03", "hi", "Hindi", "greetings", "beginner", "word", "धन्यवाद", "Dhanyavaad", "Thank you", "dhun-yuh-VAHD", "Aspirated 'dh' with voiced breath."),
    LessonItem("hi_gret_04", "hi", "Hindi", "greetings", "intermediate", "phrase", "फिर मिलेंगे", "Phir milenge", "See you again", "phir mee-LAYN-gay", "Aspirated 'ph' (like p-h, not f)."),
    LessonItem("hi_gret_05", "hi", "Hindi", "greetings", "beginner", "phrase", "शुभ प्रभात", "Shubh prabhat", "Good morning", "shoobh pruh-BHAHT", "Voiced aspirated 'bh'."),

    # Numbers
    LessonItem("hi_num_01", "hi", "Hindi", "numbers", "beginner", "word", "एक", "Ek", "One", "AYK", "Long vowel 'e', sharp 'k'."),
    LessonItem("hi_num_02", "hi", "Hindi", "numbers", "beginner", "word", "दो", "Do", "Two", "DOH", "Dental 'd' with tongue against upper teeth."),
    LessonItem("hi_num_03", "hi", "Hindi", "numbers", "beginner", "word", "तीन", "Teen", "Three", "TEEN", "Dental 't' without English puff of air."),
    LessonItem("hi_num_04", "hi", "Hindi", "numbers", "intermediate", "word", "दस", "Das", "Ten", "DUS", "Short vowel 'u' sound like cup."),
    LessonItem("hi_num_05", "hi", "Hindi", "numbers", "intermediate", "word", "पच्चीस", "Pachees", "Twenty-five", "puh-CHEES", "Geminate double 'ch' sound."),

    # Travel
    LessonItem("hi_trv_01", "hi", "Hindi", "travel", "beginner", "word", "हवाई अड्डा", "Hawai adda", "Airport", "huh-wah-EE uhd-DAH", "Retroflex 'dd' with tongue curled back."),
    LessonItem("hi_trv_02", "hi", "Hindi", "travel", "intermediate", "phrase", "रेलवे स्टेशन कहाँ है?", "Railway station kahan hai?", "Where is the railway station?", "rehl-way stay-shun kuh-HAHN hai", "Nasal tone on 'kahan'."),
    LessonItem("hi_trv_03", "hi", "Hindi", "travel", "advanced", "phrase", "मुझे एक टिकट चाहिए", "Mujhe ek ticket chahiye", "I need a ticket", "moo-JHAY ayk tee-kuht CHAH-hee-yay", "Aspirated 'jh' in mujhe."),

    # Food
    LessonItem("hi_foo_01", "hi", "Hindi", "food", "beginner", "word", "पानी", "Paani", "Water", "PAH-nee", "Long 'aa' and retroflex 'n'."),
    LessonItem("hi_foo_02", "hi", "Hindi", "food", "beginner", "word", "चाय", "Chai", "Tea", "CHY", "Crisp diphthong 'ai'."),
    LessonItem("hi_foo_03", "hi", "Hindi", "food", "intermediate", "phrase", "खाना बहुत स्वादिष्ट है", "Khaana bahut swaadisht hai", "The food is very delicious", "KHAH-nah buh-HOOT swah-DEESHT hai", "Aspirated 'kh' from deep in the throat."),
    LessonItem("hi_foo_04", "hi", "Hindi", "food", "intermediate", "phrase", "बिल ले आइए", "Bill le aaiye", "Please bring the bill", "bill lay AH-ee-yay", "Polite ending 'aaiye'."),

    # Business
    LessonItem("hi_bus_01", "hi", "Hindi", "business", "intermediate", "word", "व्यापार", "Vyaapaar", "Business / Trade", "vyah-PAHR", "Blend 'v-y' smoothly."),
    LessonItem("hi_bus_02", "hi", "Hindi", "business", "advanced", "phrase", "हमारी बैठक कब है?", "Hamaari baithak kab hai?", "When is our meeting?", "huh-MAH-ree BY-thuk kub hai", "Dental 'th' in baithak."),
    LessonItem("hi_bus_03", "hi", "Hindi", "business", "advanced", "phrase", "यह एक अच्छा सौदा है", "Yeh ek achha sauda hai", "This is a good deal", "yeh ayk UCH-chhah SOW-dah hai", "Double 'chh' aspirated."),

    # ---------------- TAMIL (ta) ----------------
    # Greetings
    LessonItem("ta_gret_01", "ta", "Tamil", "greetings", "beginner", "word", "வணக்கம்", "Vanakkam", "Hello / Greetings", "vuh-nuh-KKUM", "Double 'kk' held slightly before release."),
    LessonItem("ta_gret_02", "ta", "Tamil", "greetings", "intermediate", "phrase", "நீங்கள் எப்படி இருக்கிறீர்கள்?", "Neengal eppadi irukkireergal?", "How are you? (polite)", "neen-guhl ep-puh-dee ee-roo-kkee-reer-guhl", "Retroflex sounds in 'eppadi'."),
    LessonItem("ta_gret_03", "ta", "Tamil", "greetings", "beginner", "word", "நன்றி", "Nandri", "Thank you", "NUN-dree", "Alveolar 'dr' flap."),
    LessonItem("ta_gret_04", "ta", "Tamil", "greetings", "intermediate", "phrase", "மீண்டும் சந்திப்போம்", "Meendum santhippom", "See you again", "meen-doom sun-thip-POHM", "Nasal 'm' and long 'om'."),
    LessonItem("ta_gret_05", "ta", "Tamil", "greetings", "beginner", "phrase", "காலை வணக்கம்", "Kaalai vanakkam", "Good morning", "KAH-ly vuh-nuh-kkum", "Clear diphthong 'ai'."),

    # Numbers
    LessonItem("ta_num_01", "ta", "Tamil", "numbers", "beginner", "word", "ஒன்று", "Ondru", "One", "OHN-droo", "Trilled or flapped alveolar 'dr'."),
    LessonItem("ta_num_02", "ta", "Tamil", "numbers", "beginner", "word", "இரண்டு", "Irandu", "Two", "ee-RUHN-doo", "Retroflex 'nd' sound."),
    LessonItem("ta_num_03", "ta", "Tamil", "numbers", "beginner", "word", "மூன்று", "Moondru", "Three", "MOON-droo", "Long vowel 'oo'."),
    LessonItem("ta_num_04", "ta", "Tamil", "numbers", "intermediate", "word", "பத்து", "Pathu", "Ten", "PUH-thoo", "Dental 'th' sound."),
    LessonItem("ta_num_05", "ta", "Tamil", "numbers", "intermediate", "word", "இருபது", "Irubathu", "Twenty", "ee-roo-BUH-thoo", "Flowing cadence with dental 'th'."),

    # Travel
    LessonItem("ta_trv_01", "ta", "Tamil", "travel", "beginner", "word", "விமான நிலையம்", "Vimaana nilayam", "Airport", "vee-MAH-nuh nee-LUH-yum", "Gentle rhythmic cadence."),
    LessonItem("ta_trv_02", "ta", "Tamil", "travel", "intermediate", "phrase", "ரயில் நிலையம் எங்கே?", "Rayil nilayam engae?", "Where is the train station?", "ry-il nee-luh-yum EHN-gay", "Question rises on 'engae'."),
    LessonItem("ta_trv_03", "ta", "Tamil", "travel", "advanced", "phrase", "எனக்கு ஒரு டிக்கெட் வேண்டும்", "Enakku oru ticket vendum", "I need a ticket", "eh-NUK-koo OH-roo tee-kuht VEHN-doom", "Hold the double 'kk'."),

    # Food
    LessonItem("ta_foo_01", "ta", "Tamil", "food", "beginner", "word", "தண்ணீர்", "Thanneer", "Water", "thun-NEER", "Long 'ee' ending with soft 'r'."),
    LessonItem("ta_foo_02", "ta", "Tamil", "food", "beginner", "word", "சோறு", "Soru", "Cooked rice", "SOH-roo", "Hard retroflex 'r' at the back."),
    LessonItem("ta_foo_03", "ta", "Tamil", "food", "intermediate", "phrase", "உணவு மிகவும் சுவையாக உள்ளது", "Unavu migavum suvaiyaaga ullathu", "The food is very tasty", "oo-NUH-voo mee-guh-voom soo-vy-AH-guh ool-LUH-thoo", "Double retroflex 'll'."),
    LessonItem("ta_foo_04", "ta", "Tamil", "food", "intermediate", "phrase", "ரசீது கொடுங்கள்", "Raseedhu kodungal", "Please give the receipt", "ruh-SEE-dhoo koh-DOON-guhl", "Polite imperative suffix '-ngal'."),

    # Business
    LessonItem("ta_bus_01", "ta", "Tamil", "business", "intermediate", "word", "தொழில்", "Thozhil", "Industry / Business", "thoh-ZHEEL", "The unique retroflex approximant 'zh' (ழ)."),
    LessonItem("ta_bus_02", "ta", "Tamil", "business", "advanced", "phrase", "நமது கூட்டம் எப்போது?", "Namadhu koottam eppodhu?", "When is our meeting?", "nuh-MUH-dhoo KOOT-tum ep-POH-dhoo", "Heavy geminated 'tt' and 'pp'."),
    LessonItem("ta_bus_03", "ta", "Tamil", "business", "advanced", "phrase", "ஒப்பந்தம் தயாராக உள்ளது", "Oppantham thayaaraaga ullathu", "The contract is ready", "ohp-PUN-thum thuh-yah-RAH-guh ool-LUH-thoo", "Steady rhythmic beats."),

    # ---------------- GERMAN (de) ----------------
    # Greetings
    LessonItem("de_gret_01", "de", "German", "greetings", "beginner", "word", "Hallo", "Hallo", "Hello", "HAH-loh", "Short open 'a', distinct 'o'."),
    LessonItem("de_gret_02", "de", "German", "greetings", "beginner", "phrase", "Guten Morgen", "Guten Morgen", "Good morning", "GOO-tuhn MOHR-guhn", "Glottal stop on 'Guten', uvular 'r' in Morgen."),
    LessonItem("de_gret_03", "de", "German", "greetings", "intermediate", "phrase", "Wie geht es Ihnen?", "Wie geht es Ihnen?", "How are you? (formal)", "vee gayt ehs EE-nuhn", "Long 'ee' for 'Wie', long 'eh' for 'geht'."),
    LessonItem("de_gret_04", "de", "German", "greetings", "beginner", "word", "Danke", "Danke", "Thank you", "DAHN-kuh", "Short 'a', unstressed final 'e'."),
    LessonItem("de_gret_05", "de", "German", "greetings", "intermediate", "phrase", "Auf Wiedersehen", "Auf Wiedersehen", "Goodbye", "owf VEE-der-zay-uhn", "German 'w' sounds like English 'v'."),

    # Numbers
    LessonItem("de_num_01", "de", "German", "numbers", "beginner", "word", "Eins", "Eins", "One", "EYNS", "Clear diphthong 'ei' like eye."),
    LessonItem("de_num_02", "de", "German", "numbers", "beginner", "word", "Zwei", "Zwei", "Two", "TSVY", "German 'z' is pronounced 'ts'."),
    LessonItem("de_num_03", "de", "German", "numbers", "beginner", "word", "Fünf", "Fünf", "Five", "FYOONF", "Umlaut 'ü': shape lips for 'oo', say 'ee'."),
    LessonItem("de_num_04", "de", "German", "numbers", "intermediate", "word", "Zwanzig", "Zwanzig", "Twenty", "TSVAHN-tsikh", "Final '-ig' sounds like a soft 'ich'."),
    LessonItem("de_num_05", "de", "German", "numbers", "intermediate", "word", "Hundert", "Hundert", "Hundred", "HOON-duhrt", "Clear short 'u'."),

    # Travel
    LessonItem("de_trv_01", "de", "German", "travel", "beginner", "word", "Flughafen", "Flughafen", "Airport", "FLOOK-hah-fuhn", "Compound noun, stress first syllable."),
    LessonItem("de_trv_02", "de", "German", "travel", "intermediate", "phrase", "Wo ist der Bahnhof?", "Wo ist der Bahnhof?", "Where is the train station?", "voh eest dehr BAHN-hohf", "Long 'ah' in Bahn."),
    LessonItem("de_trv_03", "de", "German", "travel", "advanced", "phrase", "Eine Fahrkarte bitte", "Eine Fahrkarte bitte", "A ticket please", "EYE-nuh FAHR-kahr-tuh BEE-tuh", "Double 'tt' in bitte is short and crisp."),

    # Food
    LessonItem("de_foo_01", "de", "German", "food", "beginner", "word", "Wasser", "Wasser", "Water", "VAHS-suhr", "The 'w' sounds like 'v', soft final '-er'."),
    LessonItem("de_foo_02", "de", "German", "food", "beginner", "word", "Brot", "Brot", "Bread", "BROHT", "Long 'o' without English 'w' glide."),
    LessonItem("de_foo_03", "de", "German", "food", "intermediate", "phrase", "Die Rechnung bitte", "Die Rechnung bitte", "The bill please", "dee REKH-noong BEE-tuh", "Soft 'ch' (ich-Laut) made near the roof of mouth."),
    LessonItem("de_foo_04", "de", "German", "food", "intermediate", "phrase", "Einen Tisch für zwei", "Einen Tisch für zwei", "A table for two", "EYE-nuhn teesh feer tsvy", "'sch' is like English 'sh'."),

    # Business
    LessonItem("de_bus_01", "de", "German", "business", "intermediate", "word", "Unternehmen", "Unternehmen", "Company", "oon-ter-NAY-muhn", "Stress on third syllable 'neh'."),
    LessonItem("de_bus_02", "de", "German", "business", "advanced", "phrase", "Wir haben ein Treffen", "Wir haben ein Treffen", "We have a meeting", "veer HAH-buhn eyn TREH-fuhn", "Short 'e' in Treffen."),
    LessonItem("de_bus_03", "de", "German", "business", "advanced", "phrase", "Der Vertrag ist unterschrieben", "Der Vertrag ist unterschrieben", "The contract is signed", "dehr fehr-TRAHK eest oon-ter-SHREE-buhn", "Initial 'v' in Vertrag sounds like 'f'."),

    # ---------------- JAPANESE (ja) ----------------
    # Greetings
    LessonItem("ja_gret_01", "ja", "Japanese", "greetings", "beginner", "word", "こんにちは", "Konnichiwa", "Hello / Good afternoon", "kohn-nee-chee-wah", "Double 'nn' held for one mora beat. 'Wa' written with 'ha'."),
    LessonItem("ja_gret_02", "ja", "Japanese", "greetings", "beginner", "phrase", "おはようございます", "Ohayou gozaimasu", "Good morning", "oh-hah-yoh goh-zeye-mahs", "Elongated 'yoh', final 'u' in su is whispered."),
    LessonItem("ja_gret_03", "ja", "Japanese", "greetings", "beginner", "word", "ありがとう", "Arigatou", "Thank you", "ah-ree-gah-toh", "Light Japanese 'r' tap between 'l' and 'd'."),
    LessonItem("ja_gret_04", "ja", "Japanese", "greetings", "intermediate", "phrase", "お元気ですか？", "Ogenki desu ka?", "How are you?", "oh-GEN-kee dehss kah", "Polite prefix 'o-', crisp 'ka' question particle."),
    LessonItem("ja_gret_05", "ja", "Japanese", "greetings", "intermediate", "phrase", "さようなら", "Sayounara", "Goodbye", "sah-yoh-nah-rah", "Even pitch mora timing."),

    # Numbers
    LessonItem("ja_num_01", "ja", "Japanese", "numbers", "beginner", "word", "いち", "Ichi", "One", "EE-chee", "Two equal mora beats."),
    LessonItem("ja_num_02", "ja", "Japanese", "numbers", "beginner", "word", "さん", "San", "Three", "SAHN", "Nasal 'n' held for one full beat."),
    LessonItem("ja_num_03", "ja", "Japanese", "numbers", "beginner", "word", "ご", "Go", "Five", "GOH", "Clean voiced velar stop."),
    LessonItem("ja_num_04", "ja", "Japanese", "numbers", "intermediate", "word", "じゅう", "Juu", "Ten", "JYOO", "Long elongated 'uu' vowel."),
    LessonItem("ja_num_05", "ja", "Japanese", "numbers", "intermediate", "word", "ひゃく", "Hyaku", "One hundred", "HYAH-koo", "Glided single mora 'hya'."),

    # Travel
    LessonItem("ja_trv_01", "ja", "Japanese", "travel", "beginner", "word", "空港", "Kuukou", "Airport", "KOO-koh", "Elongated 'uu' and 'ou'."),
    LessonItem("ja_trv_02", "ja", "Japanese", "travel", "intermediate", "phrase", "駅はどこですか？", "Eki wa doko desu ka?", "Where is the station?", "eh-kee wah DOH-koh dehss kah", "Short crisp syllables."),
    LessonItem("ja_trv_03", "ja", "Japanese", "travel", "advanced", "phrase", "切符を一枚ください", "Kippu o ichimai kudasai", "Please give me one ticket", "keep-POO oh ee-chee-mye koo-dah-sye", "Double 'pp' glottal pause (sokuon)."),

    # Food
    LessonItem("ja_foo_01", "ja", "Japanese", "food", "beginner", "word", "お水", "Omizu", "Water", "oh-MEE-zoo", "Unvoiced or light 'z' sound."),
    LessonItem("ja_foo_02", "ja", "Japanese", "food", "beginner", "word", "お茶", "Ocha", "Green tea", "oh-CHAH", "Polite prefix 'o' followed by 'cha'."),
    LessonItem("ja_foo_03", "ja", "Japanese", "food", "intermediate", "phrase", "お勘定をお願いします", "Okanjou o onegaishimasu", "The bill please", "oh-kahn-joh oh oh-neh-guy-shee-mahs", "Polite and respectful cadence."),
    LessonItem("ja_foo_04", "ja", "Japanese", "food", "intermediate", "phrase", "とても美味しいです", "Totemo oishii desu", "It is very delicious", "toh-teh-moh oy-SHEE dehss", "Double 'ii' elongated."),

    # Business
    LessonItem("ja_bus_01", "ja", "Japanese", "business", "intermediate", "word", "会社", "Kaisha", "Company", "kye-SHAH", "Crisp 'kai-sha'."),
    LessonItem("ja_bus_02", "ja", "Japanese", "business", "advanced", "phrase", "よろしくお願いします", "Yoroshiku onegaishimasu", "I look forward to working with you", "yoh-roh-shee-koo oh-neh-guy-shee-mahs", "Quintessential Japanese business greeting; smooth flow."),
    LessonItem("ja_bus_03", "ja", "Japanese", "business", "advanced", "phrase", "名刺を交換しましょう", "Meishi o koukan shimashou", "Let us exchange business cards", "MAY-shee oh KOH-kahn shee-mah-shoh", "Elongated 'ou' sound in koukan and shimashou."),
]


class LessonBank:
    """Provides querying, filtering, and randomized quizzes over the lesson bank."""

    def __init__(self, items: Optional[List[LessonItem]] = None):
        self._items = items if items is not None else LESSON_DATA
        if not self._items:
            raise LessonDataError("Lesson bank cannot be empty.")
        app_logger.info(f"Loaded LessonBank with {len(self._items)} lesson items.")

    @property
    def all_items(self) -> List[LessonItem]:
        return list(self._items)

    def get_languages(self) -> Dict[str, str]:
        """Return dict of {code: display_name}."""
        return {
            "es": "Spanish",
            "fr": "French",
            "hi": "Hindi",
            "ta": "Tamil",
            "de": "German",
            "ja": "Japanese",
        }

    def get_categories(self) -> List[str]:
        """Return list of supported category names."""
        return ["greetings", "numbers", "travel", "food", "business"]

    def get_modes(self) -> List[str]:
        """Return supported practice modes."""
        return ["single_word", "phrase", "timed_quiz"]

    def get_items(
        self,
        language: str,
        category: Optional[str] = None,
        item_type: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[LessonItem]:
        """Filter items by language, category, type (word/phrase), and difficulty level."""
        results = [it for it in self._items if it.language.lower() == language.lower()]

        if category:
            results = [it for it in results if it.category.lower() == category.lower()]

        if item_type:
            results = [it for it in results if it.item_type.lower() == item_type.lower()]

        if level:
            results = [it for it in results if it.level.lower() == level.lower()]

        return results

    def get_quiz_items(
        self,
        language: str,
        category: Optional[str] = None,
        count: int = 10
    ) -> List[LessonItem]:
        """Generate a randomized list of items for the 10-word/phrase timed quiz mode."""
        candidates = self.get_items(language=language, category=category)
        if not candidates:
            # Fallback to any items in this language
            candidates = self.get_items(language=language)

        if not candidates:
            raise LessonDataError(f"No lesson items found for language: {language}")

        if len(candidates) <= count:
            sample = list(candidates)
            random.shuffle(sample)
            return sample

        return random.sample(candidates, count)

    def find_by_id(self, item_id: str) -> Optional[LessonItem]:
        """Retrieve an item by its unique ID."""
        for it in self._items:
            if it.id == item_id:
                return it
        return None
