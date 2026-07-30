import os

path = '/app/apps/users/templates/users/verify_email.html'
with open(path, 'r') as f:
    content = f.read()

old = """        <button type="submit" class="tc-btn btn-dark w-full">
          <span class="text-primary duration-200">Подтвердить</span>
        </button>
      </form>"""

new = """        <button type="submit" class="tc-btn btn-dark w-full">
          <span class="text-primary duration-200">Подтвердить</span>
        </button>
      </form>

      <div style="text-align:center;margin-top:16px;">
        <button type="button" id="resend-btn" onclick="resendCode()" style="background:none;border:none;color:#999;font-size:13px;cursor:pointer;text-decoration:underline;">
          Отправить код повторно
        </button>
        <p id="resend-timer" style="color:#999;font-size:12px;margin:8px 0 0;display:none;"></p>
      </div>

      <script>
      var cooldown = 60;
      var timer = cooldown;
      var timerInterval;
      function startCooldown() {
        var btn = document.getElementById('resend-btn');
        var p = document.getElementById('resend-timer');
        btn.style.display = 'none';
        p.style.display = 'block';
        timer = cooldown;
        p.textContent = 'Повторно через ' + timer + ' сек.';
        timerInterval = setInterval(function() {
          timer--;
          if (timer <= 0) {
            clearInterval(timerInterval);
            btn.style.display = 'inline';
            p.style.display = 'none';
          } else {
            p.textContent = 'Повторно через ' + timer + ' сек.';
          }
        }, 1000);
      }
      function resendCode() {
        fetch('/resend-verification/', {
          method: 'POST',
          headers: {'X-CSRFToken': '{{ csrf_token }}', 'X-Requested-With': 'XMLHttpRequest'}
        }).then(function(r) { return r.json(); }).then(function(data) {
          if (data.sent) {
            startCooldown();
          }
        }).catch(function() {
          startCooldown();
        });
      }
      startCooldown();
      </script>"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - verify_email template updated with resend button")
else:
    print("ERROR: button block not found")
