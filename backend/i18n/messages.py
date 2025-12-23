# coding: utf-8
"""Centralized multilingual message dictionary with proper UTF-8 encoding"""
from typing import Any, Dict


class Messages:
    """Central repository for multilingual responses in English, Hebrew, Russian, and Arabic."""

    # ============================================================================
    # MEDICATION MESSAGES
    # ============================================================================
    MEDICATION: Dict[str, Dict[str, str]] = {
        "missing_ingredient": {
            "en": "Please provide an active ingredient to search for.",
            "he": "נא לספק רכיב פעיל לחיפוש.",
            "ru": "Пожалуйста, укажите действующее вещество для поиска.",
            "ar": "يرجى تقديم المادة الفعالة للبحث."
        },
        "no_results": {
            "en": "No medications found with active ingredient '{ingredient}'. Please check the spelling or try another ingredient.",
            "he": "לא נמצאו תרופות עם הרכיב הפעיל '{ingredient}'. בדוק איות או נסה רכיב אחר.",
            "ru": "Не найдено лекарств с действующим веществом '{ingredient}'. Проверьте написание или попробуйте другое вещество.",
            "ar": "لم يتم العثور على أدوية تحتوي على المادة الفعالة '{ingredient}'. يرجى التحقق من الإملاء أو تجربة مادة أخرى."
        },
        "search_failed": {
            "en": "I'm having trouble searching medications right now. Please try again later.",
            "he": "קיימת בעיה בחיפוש תרופות כרגע. נסה שוב מאוחר יותר.",
            "ru": "Сейчас возникают проблемы с поиском лекарств. Пожалуйста, попробуйте позже.",
            "ar": "أواجه مشكلة في البحث عن الأدوية حالياً. يرجى المحاولة لاحقاً."
        },
        "missing_name": {
            "en": "Please provide a medication name.",
            "he": "נא לספק שם תרופה.",
            "ru": "Пожалуйста, укажите название лекарства.",
            "ar": "يرجى تقديم اسم الدواء."
        },
        "resolve_not_found": {
            "en": "I couldn't find a medication named '{name}'. Please check the spelling or try providing the active ingredient.",
            "he": "לא מצאתי תרופה בשם '{name}'. בדוק איות או ספק את הרכיב הפעיל.",
            "ru": "Не удалось найти лекарство с названием '{name}'. Проверьте написание или укажите действующее вещество.",
            "ar": "لم أتمكن من العثور على دواء باسم '{name}'. يرجى التحقق من الإملاء أو تقديم المادة الفعالة."
        },
        "resolve_failed": {
            "en": "I'm having trouble looking up that medication right now. Please try again later.",
            "he": "קיימת בעיה באיתור התרופה כרגע. נסה שוב מאוחר יותר.",
            "ru": "Сейчас возникают проблемы с поиском лекарства. Пожалуйста, попробуйте позже.",
            "ar": "أواجه مشكلة في البحث عن هذا الدواء حالياً. يرجى المحاولة لاحقاً."
        },
        "missing_query": {
            "en": "Please provide a medication name or ID.",
            "he": "נא לספק שם תרופה או מזהה.",
            "ru": "Пожалуйста, укажите название лекарства или идентификатор.",
            "ar": "يرجى تقديم اسم الدواء أو المعرّف."
        },
        "info_not_found": {
            "en": "I couldn't find information about '{query}'. Please check the spelling or try searching by active ingredient.",
            "he": "לא מצאתי מידע על '{query}'. בדוק איות או חפש לפי רכיב פעיל.",
            "ru": "Не удалось найти информацию о '{query}'. Проверьте написание или попробуйте поиск по действующему веществу.",
            "ar": "لم أتمكن من العثور على معلومات حول '{query}'. يرجى التحقق من الإملاء أو البحث بالمادة الفعالة."
        },
        "info_failed": {
            "en": "I'm having trouble retrieving medication information right now. Please try again later.",
            "he": "קיימת בעיה באחזור מידע על תרופות כרגע. נסה שוב מאוחר יותר.",
            "ru": "Сейчас возникают проблемы с получением информации о лекарстве. Пожалуйста, попробуйте позже.",
            "ar": "أواجه مشكلة في الحصول على معلومات الدواء حالياً. يرجى المحاولة لاحقاً."
        }
    }

    # ============================================================================
    # INVENTORY MESSAGES
    # ============================================================================
    INVENTORY: Dict[str, Dict[str, str]] = {
        "missing_med_id": {
            "en": "Please provide a medication ID to check stock.",
            "he": "נא לספק מזהה תרופה לבדיקת מלאי.",
            "ru": "Пожалуйста, укажите идентификатор лекарства для проверки наличия.",
            "ar": "يرجى تقديم معرّف الدواء للتحقق من المخزون."
        },
        "timeout": {
            "en": "The stock check is taking too long. Please try again in a moment.",
            "he": "בדיקת המלאי לוקחת יותר מדי זמן. נסה שוב בעוד רגע.",
            "ru": "Проверка наличия занимает слишком много времени. Пожалуйста, попробуйте чуть позже.",
            "ar": "عملية التحقق من المخزون تستغرق وقتاً طويلاً. يرجى المحاولة بعد قليل."
        },
        "service_unavailable": {
            "en": "I cannot connect to the inventory system right now. Please try again later or contact the pharmacy directly.",
            "he": "לא ניתן להתחבר למערכת המלאי כרגע. נסה שוב מאוחר יותר או פנה לבית המרקחת.",
            "ru": "Не удается подключиться к системе склада. Пожалуйста, попробуйте позже или свяжитесь с аптекой.",
            "ar": "لا يمكنني الاتصال بنظام المخزون حالياً. يرجى المحاولة لاحقاً أو التواصل مع الصيدلية مباشرة."
        },
        "not_found": {
            "en": "I couldn't find medication {med_id} in our inventory system.",
            "he": "לא מצאתי את התרופה {med_id} במערכת המלאי.",
            "ru": "Не удалось найти лекарство {med_id} в системе склада.",
            "ar": "لم أتمكن من العثور على الدواء {med_id} في نظام المخزون."
        },
        "http_error": {
            "en": "The inventory system returned an error. Please try again or contact the pharmacy.",
            "he": "מערכת המלאי החזירה שגיאה. נסה שוב או פנה לבית המרקחת.",
            "ru": "Система склада вернула ошибку. Пожалуйста, попробуйте снова или свяжитесь с аптекой.",
            "ar": "أعاد نظام المخزون خطأ. يرجى المحاولة مرة أخرى أو التواصل مع الصيدلية."
        },
        "invalid_response": {
            "en": "I received an invalid response from the inventory system. Please try again later.",
            "he": "התקבלה תשובה לא תקינה ממערכת המלאי. נסה שוב מאוחר יותר.",
            "ru": "Получен некорректный ответ от системы склада. Пожалуйста, попробуйте позже.",
            "ar": "تلقيت استجابة غير صالحة من نظام المخزون. يرجى المحاولة لاحقاً."
        },
        "unknown": {
            "en": "An unexpected error occurred while checking stock. Please try again later.",
            "he": "אירעה שגיאה לא צפויה בבדיקת מלאי. נסה שוב מאוחר יותר.",
            "ru": "Произошла непредвиденная ошибка при проверке наличия. Пожалуйста, попробуйте позже.",
            "ar": "حدث خطأ غير متوقع أثناء التحقق من المخزون. يرجى المحاولة لاحقاً."
        }
    }

    # ============================================================================
    # PHARMACY MESSAGES
    # ============================================================================
    PHARMACY: Dict[str, Dict[str, str]] = {
        "missing_location": {
            "en": "Please provide a zip code or city name to find nearby pharmacies.",
            "he": "נא לספק מיקוד או שם עיר כדי למצוא בתי מרקחת קרובים.",
            "ru": "Пожалуйста, укажите индекс или город, чтобы найти ближайшие аптеки.",
            "ar": "يرجى تقديم الرمز البريدي أو اسم المدينة للعثور على صيدليات قريبة."
        },
        "not_found": {
            "en": "I couldn't find pharmacies in '{searched_location}'. Please provide a nearby city or ZIP code. Available cities: {available}.",
            "he": "לא נמצאו בתי מרקחת ב-'{searched_location}'. נא לציין עיר קרובה או מיקוד. ערים זמינות: {available}.",
            "ru": "Аптеки в '{searched_location}' не найдены. Укажите ближайший город или индекс. Доступные города: {available}.",
            "ar": "لم يتم العثور على صيدليات في '{searched_location}'. يرجى إدخال مدينة قريبة أو الرمز البريدي. المدن المتاحة: {available}."
        },
        "found": {
            "en": "Found {count} pharmacy locations near you. The nearest is {name} at {address}.",
            "he": "נמצאו {count} בתי מרקחת בקרבתך. הקרוב ביותר הוא {name} בכתובת {address}.",
            "ru": "Найдено {count} аптек поблизости. Ближайшая — {name} по адресу {address}.",
            "ar": "تم العثور على {count} صيدليات بالقرب منك. الأقرب هي {name} على العنوان {address}."
        },
        "search_failed": {
            "en": "I'm having trouble finding nearby pharmacies right now. Please try again later.",
            "he": "קיימת בעיה במציאת בתי מרקחת קרובים כרגע. נסה שוב מאוחר יותר.",
            "ru": "Сейчас возникают проблемы с поиском ближайших аптек. Пожалуйста, попробуйте позже.",
            "ar": "أواجه مشكلة في العثور على صيدليات قريبة حالياً. يرجى المحاولة لاحقاً."
        }
    }

    # ============================================================================
    # PRESCRIPTION MESSAGES
    # ============================================================================
    PRESCRIPTION: Dict[str, Dict[str, str]] = {
        "missing_user": {
            "en": "Please log in so I can check your prescriptions.",
            "he": "נא להתחבר כדי שאוכל לבדוק מרשמים.",
            "ru": "Пожалуйста, войдите в систему, чтобы я мог проверить ваши рецепты.",
            "ar": "يرجى تسجيل الدخول حتى أتمكن من التحقق من وصفاتك."
        },
        "none_active": {
            "en": "No active prescriptions were found.",
            "he": "לא נמצאו מרשמים פעילים.",
            "ru": "Активных рецептов не найдено.",
            "ar": "لم يتم العثور على وصفات نشطة."
        },
        "none_all": {
            "en": "No prescriptions were found.",
            "he": "לא נמצאו מרשמים.",
            "ru": "Рецептов не найдено.",
            "ar": "لم يتم العثور على وصفات."
        },
        "found": {
            "en": "Found {count} prescription(s).",
            "he": "נמצאו {count} מרשמים.",
            "ru": "Найдено {count} рецептов.",
            "ar": "تم العثور على {count} وصفات."
        },
        "failed": {
            "en": "I'm having trouble retrieving prescriptions right now. Please try again later.",
            "he": "קיימת בעיה בגישה למרשמים כרגע. נסה שוב מאוחר יותר.",
            "ru": "Сейчас не удается получить рецепты. Пожалуйста, попробуйте позже.",
            "ar": "أواجه مشكلة في استرجاع الوصفات الآن. يرجى المحاولة لاحقًا."
        }
    }

    # ============================================================================
    # HANDLING MESSAGES
    # ============================================================================
    HANDLING: Dict[str, Dict[str, str]] = {
        "missing_med_id": {
            "en": "Please provide a medication ID.",
            "he": "נא לספק מזהה תרופה.",
            "ru": "Пожалуйста, укажите идентификатор лекарства.",
            "ar": "يرجى تقديم معرّف الدواء."
        },
        "not_found": {
            "en": "I couldn't find medication {med_id} in our system.",
            "he": "לא מצאתי את התרופה {med_id} במערכת שלנו.",
            "ru": "Не удалось найти лекарство {med_id} в нашей системе.",
            "ar": "لم أتمكن من العثور على الدواء {med_id} في نظامنا."
        },
        "retrieval_failed": {
            "en": "I'm having trouble retrieving handling information right now. Please try again later.",
            "he": "קיימת בעיה באחזור מידע על טיפול כרגע. נסה שוב מאוחר יותר.",
            "ru": "Сейчас возникают проблемы с получением информации о хранении. Пожалуйста, попробуйте позже.",
            "ar": "أواجه مشكلة في الحصول على معلومات التعامل حالياً. يرجى المحاولة لاحقاً."
        },
        "storage": {
            "en": "Store at room temperature away from light and moisture.",
            "he": "יש לאחסן בטמפרטורת החדר, הרחק מאור ולחות.",
            "ru": "Хранить при комнатной температуре, вдали от света и влаги.",
            "ar": "يُحفظ في درجة حرارة الغرفة بعيداً عن الضوء والرطوبة."
        },
        "child_safety": {
            "en": "Keep out of reach of children and pets.",
            "he": "יש להרחיק מהישג ידם של ילדים וחיות מחמד.",
            "ru": "Хранить в недоступном для детей и животных месте.",
            "ar": "يُحفظ بعيداً عن متناول الأطفال والحيوانات الأليفة."
        },
        "prescription": {
            "en": "Prescription medication - use only as directed by your healthcare provider.",
            "he": "תרופת מרשם - להשתמש רק לפי הנחיות איש מקצוע.",
            "ru": "Рецептурный препарат — используйте только по назначению специалиста.",
            "ar": "دواء بوصفة طبية - يُستخدم فقط حسب توجيهات مقدم الرعاية الصحية."
        },
        "message": {
            "en": "This information is from the medication label. For personalized medical advice, consult your doctor or pharmacist.",
            "he": "מידע זה מבוסס על תווית התרופה. לייעוץ רפואי אישי יש לפנות לרופא או רוקח.",
            "ru": "Эта информация взята с этикетки препарата. За персональной консультацией обратитесь к врачу или фармацевту.",
            "ar": "هذه المعلومات من ملصق الدواء. للحصول على نصيحة طبية شخصية، استشر الطبيب أو الصيدلي."
        }
    }

    # ============================================================================
    # GENERAL MESSAGES
    # ============================================================================
    GENERAL: Dict[str, Dict[str, str]] = {
        "ambiguous_match": {
            "en": "I found multiple possible matches: {options}. Which one did you mean?",
            "he": "מצאתי מספר התאמות אפשריות: {options}. לאיזו תרופה התכוונת?",
            "ru": "Я нашел несколько возможных совпадений: {options}. Какой препарат вы имели в виду?",
            "ar": "وجدت عدة مطابقات محتملة: {options}. أي دواء تقصد?"
        },
        "not_found": {
            "en": "{resource} not found: {id}",
            "he": "{resource} לא נמצא: {id}",
            "ru": "{resource} не найдено: {id}",
            "ar": "{resource} غير موجود: {id}"
        }
    }

    # ============================================================================
    # SAFETY MESSAGES
    # ============================================================================
    SAFETY: Dict[str, Dict[str, str]] = {
        "refusal_base": {
            "en": "I can't provide medical advice, diagnosis, or recommendations. Please consult a licensed pharmacist or doctor.",
            "he": "אני לא יכול/ה לספק ייעוץ רפואי, אבחון או המלצות. נא לפנות לרופא או רוקח מורשה.",
            "ru": "Я не могу предоставлять медицинские советы, диагнозы или рекомендации. Пожалуйста, обратитесь к врачу или лицензированному фармацевту.",
            "ar": "لا أستطيع تقديم نصيحة طبية أو تشخيص أو توصيات. يرجى استشارة طبيب أو صيدلي مرخص."
        },
        "refusal_suffix": {
            "en": "(request blocked: {reason}).",
            "he": "(הבקשה נחסמה: {reason}).",
            "ru": "(запрос заблокирован: {reason}).",
            "ar": "(تم حظر الطلب: {reason})."
        }
    }

    @staticmethod
    def get(category: str, key: str, lang: str = "en", **kwargs: Any) -> str:
        """
        Get translated message with fallback to English.

        Args:
            category: Message category (MEDICATION, INVENTORY, PHARMACY, etc.)
            key: Message key within the category
            lang: Language code (en, he, ru, ar)
            **kwargs: Format arguments for string interpolation

        Returns:
            Translated message string, formatted with kwargs if provided

        Example:
            >>> Messages.get('MEDICATION', 'not_found', 'he', name='Aspirin')
            "לא מצאתי תרופה בשם 'Aspirin'..."
        """
        category_dict = getattr(Messages, category.upper(), {})
        entry = category_dict.get(key, {})

        if isinstance(entry, dict):
            text = entry.get(lang, entry.get("en", ""))
        else:
            text = entry or ""

        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                # If formatting fails, return unformatted text
                return text

        return text
