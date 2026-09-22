// Flash-message popup. Server views redirect with
//   ?msg=<text>&msg_type=error|success|info
// We surface the message via alert(...) and strip the params from the URL
// so a page refresh doesn't repeat them.

(function () {
    var params = new URLSearchParams(window.location.search);
    var msg = params.get('msg');
    if (!msg) return;

    var msgType = params.get('msg_type') || 'info';
    params.delete('msg');
    params.delete('msg_type');

    var search = params.toString();
    var newUrl = window.location.pathname + (search ? '?' + search : '') + window.location.hash;
    window.history.replaceState(null, '', newUrl);

    var prefix = msgType === 'error' ? 'Error: ' : (msgType === 'success' ? 'Success: ' : '');
    window.alert(prefix + msg);
})();
