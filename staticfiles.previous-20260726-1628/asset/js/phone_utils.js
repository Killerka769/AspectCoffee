// ═══ TC Phone Utility — single source of truth ═══
var TCPhone = {
    codes: [
        {code: '+7',   country: 'Россия',          length: 10, fmt: '(000) 000-00-00'},
        {code: '+1',   country: 'США',             length: 10, fmt: '(000) 000-0000'},
        {code: '+44',  country: 'Великобритания',   length: 10, fmt: '0000 000 0000'},
        {code: '+49',  country: 'Германия',         length: 11, fmt: '0000 000 0000'},
        {code: '+33',  country: 'Франция',          length: 9,  fmt: '00 00 00 00 00'},
        {code: '+380', country: 'Украина',          length: 9,  fmt: '00 000 00 00'},
        {code: '+375', country: 'Беларусь',         length: 9,  fmt: '00 000 00 00'},
        {code: '+77',  country: 'Казахстан',        length: 10, fmt: '(000) 000-00-00', noDetect: true},
        {code: '+998', country: 'Узбекистан',       length: 9,  fmt: '00 000 00 00'},
        {code: '+992', country: 'Таджикистан',      length: 9,  fmt: '00 000 00 00'},
        {code: '+996', country: 'Кыргызстан',       length: 9,  fmt: '00 000 00 00'},
        {code: '+993', country: 'Туркменистан',     length: 8,  fmt: '00 00 00 00'}
    ],

    // Detect country code from stored phone string
    // e.g. "+77266632123" → {code: "+7", localNumber: "7266632123"}
    // e.g. "89013573577"  → {code: "+7", localNumber: "9013573577"}
    detectCode: function(phone) {
        if (!phone) return null;
        var raw = phone.replace(/[\s\-\(\)]/g, '');
        // Check from longest code to shortest
        var sorted = this.codes.slice().sort(function(a, b) { return b.code.length - a.code.length; });
        for (var i = 0; i < sorted.length; i++) {
            var c = sorted[i];
            if (c.noDetect) continue; // '+77' (KZ) must not shadow '+7' auto-detection
            var codeDigits = c.code.replace('+', '');
            if (raw.indexOf(c.code) === 0) {
                return { code: c.code, local: raw.substring(c.code.length), length: c.length };
            }
            if (raw.indexOf(codeDigits) === 0 && raw[0] !== '+') {
                return { code: '+' + codeDigits, local: raw.substring(codeDigits.length), length: c.length };
            }
        }
        // Old Russian: starts with 8 and has 11+ digits
        if (raw[0] === '8' && raw.length >= 11) {
            return { code: '+7', local: raw.substring(1), length: 10 };
        }
        return null;
    },

    // Strip country code from input element value, set correct phoneCode/phoneLength on Alpine data
    // Call from x-init or $nextTick after page load
    stripInput: function(alpineData, inputName) {
        inputName = inputName || 'phone';
        var phoneInput = document.querySelector('input[name="' + inputName + '"]');
        if (!phoneInput || !phoneInput.value) return;
        var detected = this.detectCode(phoneInput.value);
        if (detected) {
            alpineData.phoneCode = detected.code;
            alpineData.phoneLength = detected.length;
            phoneInput.value = detected.local;
        }
    },

    // Format phone number as user types (tcPhoneMask replacement)
    mask: function(e, phoneLength) {
        var el = e.target || e;
        var v = el.value.replace(/[^0-9]/g, '').substring(0, phoneLength);
        var f = '';
        if (phoneLength === 10) {
            f = '(' + v.substring(0, 3);
            if (v.length > 3) f += ') ' + v.substring(3, 6);
            if (v.length > 6) f += '-' + v.substring(6);
        } else {
            for (var i = 0; i < v.length; i++) {
                if (i === 2 || i === 5) f += ' ';
                f += v[i];
            }
        }
        el.value = f;
    },

    // Select phone code (Alpine helper)
    selectCode: function(code, alpineData) {
        alpineData.phoneCode = code;
        var c = this.codes.find(function(c) { return c.code === code; });
        alpineData.phoneLength = c ? c.length : 10;
        alpineData.phoneCodeOpen = false;
    }
};

// Backward compat
function tcPhoneMask(e) {
    var input = e.target || e;
    var phoneLength = parseInt(input.getAttribute('data-phone-length')) || 10;
    TCPhone.mask(e, phoneLength);
}

function tcProfilePhoneMask(e) {
    TCPhone.mask(e, 10);
}
