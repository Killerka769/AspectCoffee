"""Single source of truth for phone countries used by every site form."""

PHONE_COUNTRIES = (
    {
        "code": "+7",
        "country": "Россия / Казахстан",
        "length": 10,
        "fmt": "(000) 000-00-00",
        "placeholder": "(900) 000-00-00",
    },
    {
        "code": "+1",
        "country": "США / Канада",
        "length": 10,
        "fmt": "(000) 000-0000",
        "placeholder": "(201) 555-0123",
    },
    {
        "code": "+44",
        "country": "Великобритания",
        "length": 10,
        "fmt": "0000 000 000",
        "placeholder": "7700 900 123",
    },
    {
        "code": "+49",
        "country": "Германия",
        "length": 11,
        "fmt": "0000 0000000",
        "placeholder": "1512 3456789",
    },
    {
        "code": "+33",
        "country": "Франция",
        "length": 9,
        "fmt": "0 00 00 00 00",
        "placeholder": "6 12 34 56 78",
    },
    {
        "code": "+380",
        "country": "Украина",
        "length": 9,
        "fmt": "00 000 00 00",
        "placeholder": "67 123 45 67",
    },
    {
        "code": "+375",
        "country": "Беларусь",
        "length": 9,
        "fmt": "00 000-00-00",
        "placeholder": "29 123-45-67",
    },
    {
        "code": "+998",
        "country": "Узбекистан",
        "length": 9,
        "fmt": "00 000-00-00",
        "placeholder": "90 123-45-67",
    },
    {
        "code": "+992",
        "country": "Таджикистан",
        "length": 9,
        "fmt": "00 000-00-00",
        "placeholder": "90 123-45-67",
    },
    {
        "code": "+996",
        "country": "Кыргызстан",
        "length": 9,
        "fmt": "000 00-00-00",
        "placeholder": "555 12-34-56",
    },
    {
        "code": "+993",
        "country": "Туркменистан",
        "length": 8,
        "fmt": "00 00-00-00",
        "placeholder": "65 12-34-56",
    },
)

PHONE_COUNTRY_BY_CODE = {
    country["code"]: country for country in PHONE_COUNTRIES
}


def phone_country(code):
    return PHONE_COUNTRY_BY_CODE.get((code or "").strip())

