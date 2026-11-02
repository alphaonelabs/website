(function () {
  var RULES = [
    {id: 'length',label: 'At least 8 characters', test: function (p) { return p.length >= 8; } },
    {id: 'upper',label: 'One uppercase letter (A-Z)', test: function (p) { return /[A-Z]/.test(p); } },
    {id: 'lower',label: 'One lowercase letter (a-z)', test: function (p) { return /[a-z]/.test(p); } },
    {id: 'digit',label: 'One number (0-9)', test: function (p) { return /[0-9]/.test(p); } },
    {id: 'symbol',label: 'One symbol (e.g. ! @ # $ %)', test: function (p) { return /[^A-Za-z0-9\s]/.test(p); } }
  ];

  // Mirrors validate_password_strength() in src/worker.py (the server also checks a common-password list).
  function validate(pw, username) {
    pw = pw || '';
    if (pw.length < 8) return 'Password must be at least 8 characters';
    if (pw.length > 128) return 'Password must be at most 128 characters';
    if (!/[A-Z]/.test(pw)) return 'Password must include an uppercase letter';
    if (!/[a-z]/.test(pw)) return 'Password must include a lowercase letter';
    if (!/[0-9]/.test(pw)) return 'Password must include a number';
    if (!/[^A-Za-z0-9\s]/.test(pw)) return 'Password must include a symbol (for example ! @ # $ %)';
    var u = (username || '').trim().toLowerCase();
    if (u.length >= 3 && pw.toLowerCase().indexOf(u) !== -1) return 'Password must not contain your username';
    return null;
  }

  // Renders a live checklist into `container` (a <ul>) that updates as the user types.
  function attachChecklist(input, container) {
    if (!input || !container) return;
    container.innerHTML = RULES.map(function (r) {
      return '<li data-rule="' + r.id + '" class="flex items-center gap-2"><i class="far fa-circle text-xs"></i><span>' + r.label + '</span></li>';
    }).join('');
    function update() {
      var pw = input.value || '';
      RULES.forEach(function (r) {
        var li = container.querySelector('[data-rule="' + r.id + '"]');
        var ok = r.test(pw);
        li.className = 'flex items-center gap-2 ' + (ok ? 'text-gray-600 dark:text-gray-400' : 'text-gray-500 dark:text-gray-400');
        li.querySelector('i').className = (ok ? 'fas fa-check-circle' : 'far fa-circle') + ' text-xs';
      });
    }
    input.addEventListener('input', update);
    update();
  }

  window.PasswordRules = { validate: validate, attachChecklist: attachChecklist };
})();