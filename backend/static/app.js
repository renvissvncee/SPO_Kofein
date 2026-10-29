const statusElement = document.querySelector("#status");
const profileElement = document.querySelector("#profile");
const userNameElement = document.querySelector("#user-name");
const telegram = window.Telegram?.WebApp;

function showError(message) {
  statusElement.textContent = message;
  statusElement.classList.add("error");
}

async function authenticate() {
  if (!telegram?.initData) {
    showError("Откройте эту страницу через кнопку Telegram-бота.");
    return;
  }

  telegram.ready();
  telegram.expand();

  try {
    const response = await fetch("/api/v1/auth/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: telegram.initData }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error?.message || "Telegram-аутентификация не прошла");
    }

    sessionStorage.setItem("kofein_access_token", data.access_token);
    window.kofeinApi = {
      token: data.access_token,
      user: data.user,
      fetch: (url, options = {}) =>
        fetch(url, {
          ...options,
          headers: {
            ...options.headers,
            Authorization: `Bearer ${data.access_token}`,
          },
        }),
    };

    statusElement.textContent = "Аутентификация успешна";
    userNameElement.textContent = data.user.first_name;
    profileElement.hidden = false;
  } catch (error) {
    showError(error.message);
  }
}

authenticate();
