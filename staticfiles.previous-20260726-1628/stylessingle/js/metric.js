(function () {
    var t = document.createElement('script');
    t.type = 'text/javascript';
    t.defer = true;
    t.src = 'https:
    t.onload = function () {
        if (window.VK && window.VK.Retargeting && typeof window.VK.Retargeting.Init === 'function') {
            window.VK.Retargeting.Init('VK-RTRG-432834-hqEHz');
            window.VK.Retargeting.Hit();
        } else {
            console.warn('VK Retargeting is not available');
        }
    };
    document.head.appendChild(t);
})();


var _tmr = window._tmr || (window._tmr = [])
_tmr.push({id: '3416915', type: 'pageView', start: (new Date()).getTime()});
(function (d, w, id) {
    if (d.getElementById(id)) {
        return
    }
    var ts = d.createElement('script')
    ts.type = 'text/javascript'
    ts.defer = true
    ts.id = id
    ts.src = 'https:
    var f = function () {
        var s = d.getElementsByTagName('script')[0]
        s.parentNode.insertBefore(ts, s)
    }
    if (w.opera == '[object Opera]') {
        d.addEventListener('DOMContentLoaded', f, false)
    } else {
        f()
    }
})(document, window, 'tmr-code')

var fff1 = function (m, e, t, r, i, k, a) {
    m[i] = m[i] || function () {
        (m[i].a = m[i].a || []).push(arguments)
    }
    m[i].l = 1 * new Date()
    for (var j = 0; j < document.scripts.length; j++) {
        if (document.scripts[j].src === r) {
            return
        }
    }
    k = e.createElement(t), a = e.getElementsByTagName(t)[0], k.defer = 1, k.src = r, a.parentNode.insertBefore(k, a)
}

fff1(window, document, 'script', 'https:

window.ym(52141249, 'init', {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: true,
    ecommerce: 'dataLayer',
})

window.__mixm__ = window.__mixm__ || []
window.__mixm__.push(['mAdvId', 1294983657])
