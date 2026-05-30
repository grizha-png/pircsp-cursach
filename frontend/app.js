const API_BASE = (() => {
  const runtimeOverride = window.__APP_API_BASE__ || localStorage.getItem("edutest_api_base");
  if (runtimeOverride) {
    return runtimeOverride.endsWith("/api") ? runtimeOverride : `${runtimeOverride}/api`;
  }

  if (["127.0.0.1", "localhost"].includes(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
  }

  return "/api";
})();
const TOKEN_KEY = "edutest_token";

const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  user: null,
  users: [],
  tests: [],
  attempts: [],
  editingTest: null,
  selectedStudentTest: null,
  selectedTeacherTestId: null,
  editingUserId: null,
};

const elements = {
  notice: document.getElementById("notice"),
  loginPanel: document.getElementById("login-panel"),
  dashboard: document.getElementById("dashboard"),
  loginForm: document.getElementById("login-form"),
  logoutButton: document.getElementById("logout-button"),
  sessionName: document.getElementById("session-name"),
  sessionRole: document.getElementById("session-role"),
  statUsers: document.getElementById("stat-users"),
  statTests: document.getElementById("stat-tests"),
  statAttempts: document.getElementById("stat-attempts"),
  adminSection: document.getElementById("admin-section"),
  teacherSection: document.getElementById("teacher-section"),
  studentSection: document.getElementById("student-section"),
  usersTableBody: document.getElementById("users-table-body"),
  userForm: document.getElementById("user-form"),
  userId: document.getElementById("user-id"),
  userUsername: document.getElementById("user-username"),
  userFullName: document.getElementById("user-full-name"),
  userPassword: document.getElementById("user-password"),
  userRole: document.getElementById("user-role"),
  userActive: document.getElementById("user-active"),
  userSubmitButton: document.getElementById("user-submit-button"),
  userResetButton: document.getElementById("user-reset-button"),
  teacherTestsList: document.getElementById("teacher-tests-list"),
  teacherAttempts: document.getElementById("teacher-attempts"),
  newTestButton: document.getElementById("new-test-button"),
  testEditorForm: document.getElementById("test-editor-form"),
  testId: document.getElementById("test-id"),
  testTitle: document.getElementById("test-title"),
  testDescription: document.getElementById("test-description"),
  testPublished: document.getElementById("test-published"),
  questionsContainer: document.getElementById("questions-container"),
  addQuestionButton: document.getElementById("add-question-button"),
  resetTestButton: document.getElementById("reset-test-button"),
  studentTestsList: document.getElementById("student-tests-list"),
  studentTestDetail: document.getElementById("student-test-detail"),
  studentAttempts: document.getElementById("student-attempts"),
};

function makeEmptyOption(text = "", isCorrect = false) {
  return { text, is_correct: isCorrect };
}

function makeEmptyQuestion() {
  return {
    prompt: "",
    explanation: "",
    options: [makeEmptyOption("", true), makeEmptyOption("", false)],
  };
}

function makeEmptyTest() {
  return {
    id: null,
    title: "",
    description: "",
    is_published: false,
    questions: [makeEmptyQuestion()],
  };
}

function formatRole(role) {
  return {
    admin: "Администратор",
    teacher: "Преподаватель",
    student: "Студент",
  }[role] || role;
}

function formatDate(value) {
  return new Date(value).toLocaleString("ru-RU");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setToken(token) {
  state.token = token;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function showNotice(message, type = "success") {
  elements.notice.textContent = message;
  elements.notice.className = `notice ${type}`;
  window.clearTimeout(showNotice.timeoutId);
  showNotice.timeoutId = window.setTimeout(() => {
    elements.notice.className = "notice hidden";
    elements.notice.textContent = "";
  }, 4200);
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const raw = await response.text();
  let data = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch (_error) {
      data = { detail: raw };
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearSession();
      render();
    }
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join("; ")
      : data?.detail || "Запрос завершился ошибкой.";
    throw new Error(detail);
  }

  return data;
}

function clearSession() {
  state.user = null;
  state.users = [];
  state.tests = [];
  state.attempts = [];
  state.selectedStudentTest = null;
  state.selectedTeacherTestId = null;
  state.editingUserId = null;
  state.editingTest = makeEmptyTest();
  setToken("");
}

function setRoleSections() {
  const role = state.user?.role;
  elements.adminSection.classList.toggle("hidden", role !== "admin");
  elements.teacherSection.classList.toggle("hidden", !["teacher", "admin"].includes(role));
  elements.studentSection.classList.toggle("hidden", role !== "student");
}

function renderStats() {
  const usersCount = state.user?.role === "admin" ? state.users.length : 0;
  const testsCount = state.tests.length;
  const attemptsCount =
    state.user?.role === "student"
      ? state.attempts.length
      : state.selectedTeacherTestId
        ? Number(elements.teacherAttempts.dataset.count || 0)
        : 0;
  elements.statUsers.textContent = String(usersCount);
  elements.statTests.textContent = String(testsCount);
  elements.statAttempts.textContent = String(attemptsCount);
}

function resetUserForm() {
  state.editingUserId = null;
  elements.userId.value = "";
  elements.userUsername.value = "";
  elements.userUsername.disabled = false;
  elements.userFullName.value = "";
  elements.userPassword.value = "";
  elements.userPassword.required = true;
  elements.userRole.value = "student";
  elements.userActive.checked = true;
  elements.userSubmitButton.textContent = "Создать пользователя";
}

function fillUserForm(user) {
  state.editingUserId = user.id;
  elements.userId.value = String(user.id);
  elements.userUsername.value = user.username;
  elements.userUsername.disabled = true;
  elements.userFullName.value = user.full_name;
  elements.userPassword.value = "";
  elements.userPassword.required = false;
  elements.userRole.value = user.role;
  elements.userActive.checked = user.is_active;
  elements.userSubmitButton.textContent = "Сохранить изменения";
}

function renderUsers() {
  if (!state.users.length) {
    elements.usersTableBody.innerHTML = `<tr><td colspan="6">Пользователи не найдены.</td></tr>`;
    return;
  }

  elements.usersTableBody.innerHTML = state.users
    .map(
      (user) => `
        <tr>
          <td>${user.id}</td>
          <td>${escapeHtml(user.username)}</td>
          <td>${escapeHtml(user.full_name)}</td>
          <td>${user.role}</td>
          <td>${user.is_active ? "active" : "inactive"}</td>
          <td class="actions-cell">
            <button class="button button-secondary" data-action="edit-user" data-id="${user.id}" type="button">Изменить</button>
            <button class="button button-danger" data-action="delete-user" data-id="${user.id}" type="button">Удалить</button>
          </td>
        </tr>
      `,
    )
    .join("");
}

function renderTeacherTests() {
  if (!state.tests.length) {
    elements.teacherTestsList.innerHTML = `<div class="empty-state">Тестов пока нет. Создайте первый тест в редакторе справа.</div>`;
    return;
  }

  elements.teacherTestsList.innerHTML = state.tests
    .map(
      (test) => `
        <article class="test-card">
          <header>
            <div>
              <h3>${escapeHtml(test.title)}</h3>
              <div class="meta-line">
                <span>Вопросов: ${test.question_count}</span>
                <span>Попыток: ${test.attempt_count}</span>
                <span>${test.is_published ? "Опубликован" : "Черновик"}</span>
              </div>
            </div>
            <span class="badge">${escapeHtml(test.owner_name)}</span>
          </header>
          <p>${escapeHtml(test.description || "Без описания")}</p>
          <div class="button-row">
            <button class="button button-secondary" data-action="edit-test" data-id="${test.id}" type="button">Редактировать</button>
            <button class="button button-secondary" data-action="toggle-publish" data-id="${test.id}" data-published="${test.is_published}" type="button">
              ${test.is_published ? "Снять с публикации" : "Опубликовать"}
            </button>
            <button class="button button-secondary" data-action="view-attempts" data-id="${test.id}" type="button">Результаты</button>
            <button class="button button-danger" data-action="delete-test" data-id="${test.id}" type="button">Удалить</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function questionTemplate(question, questionIndex) {
  const options = question.options
    .map(
      (option, optionIndex) => `
        <div class="option-row">
          <input
            type="radio"
            name="question-correct-${questionIndex}"
            ${option.is_correct ? "checked" : ""}
            aria-label="Правильный ответ"
          />
          <input
            type="text"
            class="option-text-input"
            value="${escapeHtml(option.text)}"
            placeholder="Текст варианта"
            required
          />
          <button class="button button-danger" data-action="remove-option" data-question-index="${questionIndex}" data-option-index="${optionIndex}" type="button">
            Удалить вариант
          </button>
        </div>
      `,
    )
    .join("");

  return `
    <article class="question-card" data-question-index="${questionIndex}">
      <div class="question-card-header">
        <h3>Вопрос ${questionIndex + 1}</h3>
        <button class="button button-danger" data-action="remove-question" data-question-index="${questionIndex}" type="button">
          Удалить вопрос
        </button>
      </div>
      <label>
        <span>Формулировка</span>
        <textarea class="question-prompt-input" rows="2" required>${escapeHtml(question.prompt)}</textarea>
      </label>
      <label>
        <span>Пояснение после ответа</span>
        <textarea class="question-explanation-input" rows="2">${escapeHtml(question.explanation || "")}</textarea>
      </label>
      <div class="card-stack">
        ${options}
      </div>
      <button class="button button-secondary" data-action="add-option" data-question-index="${questionIndex}" type="button">
        Добавить вариант
      </button>
    </article>
  `;
}

function renderTestEditor() {
  const test = state.editingTest || makeEmptyTest();
  elements.testId.value = test.id || "";
  elements.testTitle.value = test.title || "";
  elements.testDescription.value = test.description || "";
  elements.testPublished.checked = Boolean(test.is_published);
  elements.questionsContainer.innerHTML = test.questions
    .map((question, index) => questionTemplate(question, index))
    .join("");
}

function syncEditingTestFromDom() {
  const test = state.editingTest || makeEmptyTest();
  test.title = elements.testTitle.value.trim();
  test.description = elements.testDescription.value.trim();
  test.is_published = elements.testPublished.checked;
  test.questions = Array.from(elements.questionsContainer.querySelectorAll(".question-card")).map((card) => {
    const optionRows = Array.from(card.querySelectorAll(".option-row"));
    const options = optionRows.map((row) => {
      const text = row.querySelector(".option-text-input").value.trim();
      const isCorrect = row.querySelector('input[type="radio"]').checked;
      return { text, is_correct: isCorrect };
    });
    return {
      prompt: card.querySelector(".question-prompt-input").value.trim(),
      explanation: card.querySelector(".question-explanation-input").value.trim(),
      options,
    };
  });
  state.editingTest = test;
}

function validateEditableTest(test) {
  if (!test.title) {
    throw new Error("У теста должно быть название.");
  }
  if (!test.questions.length) {
    throw new Error("Добавьте хотя бы один вопрос.");
  }

  test.questions.forEach((question, index) => {
    if (!question.prompt) {
      throw new Error(`Заполните текст вопроса ${index + 1}.`);
    }
    if (question.options.length < 2) {
      throw new Error(`В вопросе ${index + 1} должно быть минимум два варианта ответа.`);
    }
    const correctCount = question.options.filter((item) => item.is_correct).length;
    if (correctCount !== 1) {
      throw new Error(`В вопросе ${index + 1} должен быть ровно один правильный ответ.`);
    }
    if (question.options.some((item) => !item.text.trim())) {
      throw new Error(`В вопросе ${index + 1} есть пустой вариант ответа.`);
    }
  });
}

function renderTeacherAttempts(attempts) {
  elements.teacherAttempts.dataset.count = String(attempts.length);
  if (!attempts.length) {
    elements.teacherAttempts.innerHTML = `<div class="empty-state">По этому тесту пока нет попыток.</div>`;
    renderStats();
    return;
  }

  elements.teacherAttempts.innerHTML = attempts
    .map(
      (attempt) => `
        <article class="attempt-card">
          <strong>${escapeHtml(attempt.student_name)} — ${attempt.score}/${attempt.total_questions}</strong>
          <div class="meta-line">
            <span>Попытка #${attempt.id}</span>
            <span>${formatDate(attempt.submitted_at)}</span>
          </div>
        </article>
      `,
    )
    .join("");
  renderStats();
}

function renderStudentTests() {
  if (!state.tests.length) {
    elements.studentTestsList.innerHTML = `<div class="empty-state">Пока нет опубликованных тестов.</div>`;
    return;
  }

  elements.studentTestsList.innerHTML = state.tests
    .map(
      (test) => `
        <article class="test-card">
          <header>
            <div>
              <h3>${escapeHtml(test.title)}</h3>
              <div class="meta-line">
                <span>Вопросов: ${test.question_count}</span>
                <span>Автор: ${escapeHtml(test.owner_name)}</span>
              </div>
            </div>
          </header>
          <p>${escapeHtml(test.description || "Без описания")}</p>
          <div class="button-row">
            <button class="button button-primary" data-action="open-student-test" data-id="${test.id}" type="button">Открыть тест</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderStudentTestDetail(test) {
  const questionsMarkup = test.questions
    .map(
      (question, questionIndex) => `
        <div class="student-question">
          <h3>${questionIndex + 1}. ${escapeHtml(question.prompt)}</h3>
          <div class="student-options">
            ${question.options
              .map(
                (option) => `
                  <label class="student-option">
                    <input type="radio" name="student-question-${question.id}" value="${option.id}" />
                    <span>${escapeHtml(option.text)}</span>
                  </label>
                `,
              )
              .join("")}
          </div>
        </div>
      `,
    )
    .join("");

  elements.studentTestDetail.className = "student-test-board";
  elements.studentTestDetail.innerHTML = `
    <form id="student-submit-form">
      <div class="panel-head compact">
        <div>
          <p class="panel-label">Активный тест</p>
          <h3>${escapeHtml(test.title)}</h3>
        </div>
        <span class="badge">${test.questions.length} вопросов</span>
      </div>
      <p>${escapeHtml(test.description || "Без описания")}</p>
      ${questionsMarkup}
      <div class="button-row" style="margin-top: 18px;">
        <button class="button button-primary" type="submit">Отправить ответы</button>
      </div>
    </form>
  `;

  document.getElementById("student-submit-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const answers = test.questions.map((question) => {
        const selected = document.querySelector(`input[name="student-question-${question.id}"]:checked`);
        if (!selected) {
          throw new Error("Нужно выбрать ответ для каждого вопроса.");
        }
        return {
          question_id: question.id,
          option_id: Number(selected.value),
        };
      });

      const attempt = await api(`/tests/${test.id}/submit`, {
        method: "POST",
        body: JSON.stringify({ answers }),
      });

      showNotice(`Тест отправлен. Ваш результат: ${attempt.score}/${attempt.total_questions}.`);
      await loadStudentAttempts();
      elements.studentTestDetail.innerHTML = `
        <div class="empty-state">
          Результат сохранен: <strong>${attempt.score}/${attempt.total_questions}</strong>. Можно выбрать другой тест или пройти этот снова.
        </div>
      `;
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
}

function renderStudentAttempts() {
  if (!state.attempts.length) {
    elements.studentAttempts.innerHTML = `<div class="empty-state">Попыток пока нет.</div>`;
    return;
  }

  elements.studentAttempts.innerHTML = state.attempts
    .map(
      (attempt) => `
        <article class="attempt-card">
          <strong>${escapeHtml(attempt.test_title)} — ${attempt.score}/${attempt.total_questions}</strong>
          <div class="meta-line">
            <span>Попытка #${attempt.id}</span>
            <span>${formatDate(attempt.submitted_at)}</span>
          </div>
        </article>
      `,
    )
    .join("");
}

async function loadUsers() {
  state.users = await api("/users");
  renderUsers();
}

async function loadTests() {
  state.tests = await api("/tests");
  if (["teacher", "admin"].includes(state.user.role)) {
    renderTeacherTests();
  }
  if (state.user.role === "student") {
    renderStudentTests();
  }
  renderStats();
}

async function loadTeacherAttempts(testId) {
  const attempts = await api(`/tests/${testId}/attempts`);
  renderTeacherAttempts(attempts);
}

async function loadStudentAttempts() {
  state.attempts = await api("/attempts/me");
  renderStudentAttempts();
  renderStats();
}

function render() {
  const isAuthenticated = Boolean(state.user);
  elements.loginPanel.classList.toggle("hidden", isAuthenticated);
  elements.dashboard.classList.toggle("hidden", !isAuthenticated);

  if (!isAuthenticated) {
    return;
  }

  elements.sessionName.textContent = state.user.full_name;
  elements.sessionRole.textContent = formatRole(state.user.role);
  setRoleSections();
  renderStats();
}

async function restoreSession() {
  if (!state.token) {
    state.editingTest = makeEmptyTest();
    render();
    return;
  }

  try {
    state.user = await api("/auth/me");
    state.editingTest = makeEmptyTest();
    render();

    if (state.user.role === "admin") {
      await Promise.all([loadUsers(), loadTests()]);
    } else if (state.user.role === "teacher") {
      await loadTests();
    } else if (state.user.role === "student") {
      await Promise.all([loadTests(), loadStudentAttempts()]);
    }
  } catch (error) {
    clearSession();
    render();
  }
}

elements.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      username: document.getElementById("login-username").value.trim(),
      password: document.getElementById("login-password").value,
    };
    const result = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(result.token);
    state.user = result.user;
    state.editingTest = makeEmptyTest();
    render();
    resetUserForm();
    renderTestEditor();

    if (state.user.role === "admin") {
      await Promise.all([loadUsers(), loadTests()]);
    } else if (state.user.role === "teacher") {
      await loadTests();
    } else {
      await Promise.all([loadTests(), loadStudentAttempts()]);
    }

    showNotice(`Вход выполнен. Активная роль: ${formatRole(state.user.role)}.`);
    elements.loginForm.reset();
  } catch (error) {
    showNotice(error.message, "error");
  }
});

elements.logoutButton.addEventListener("click", async () => {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch (_error) {
    // Silent by design: even if the token has expired locally, we still clear the UI state.
  } finally {
    clearSession();
    resetUserForm();
    renderTestEditor();
    elements.studentTestDetail.className = "student-test-board empty-state";
    elements.studentTestDetail.textContent = "Выберите тест слева, чтобы пройти его.";
    render();
    showNotice("Сессия завершена.");
  }
});

elements.userForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      full_name: elements.userFullName.value.trim(),
      role: elements.userRole.value,
      is_active: elements.userActive.checked,
    };

    if (state.editingUserId) {
      if (elements.userPassword.value.trim()) {
        payload.password = elements.userPassword.value;
      }
      await api(`/users/${state.editingUserId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showNotice("Пользователь обновлен.");
    } else {
      payload.username = elements.userUsername.value.trim();
      payload.password = elements.userPassword.value;
      await api("/users", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showNotice("Пользователь создан.");
    }

    resetUserForm();
    await loadUsers();
    renderStats();
  } catch (error) {
    showNotice(error.message, "error");
  }
});

elements.userResetButton.addEventListener("click", () => {
  resetUserForm();
});

elements.usersTableBody.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }

  const userId = Number(button.dataset.id);
  const action = button.dataset.action;

  if (action === "edit-user") {
    const user = state.users.find((item) => item.id === userId);
    if (user) {
      fillUserForm(user);
    }
    return;
  }

  if (action === "delete-user") {
    if (!window.confirm("Удалить пользователя?")) {
      return;
    }
    try {
      await api(`/users/${userId}`, { method: "DELETE" });
      showNotice("Пользователь удален.");
      await loadUsers();
      renderStats();
    } catch (error) {
      showNotice(error.message, "error");
    }
  }
});

elements.newTestButton.addEventListener("click", () => {
  state.editingTest = makeEmptyTest();
  renderTestEditor();
});

elements.addQuestionButton.addEventListener("click", () => {
  syncEditingTestFromDom();
  state.editingTest.questions.push(makeEmptyQuestion());
  renderTestEditor();
});

elements.resetTestButton.addEventListener("click", () => {
  state.editingTest = makeEmptyTest();
  renderTestEditor();
});

elements.questionsContainer.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }
  const action = button.dataset.action;
  const questionIndex = Number(button.dataset.questionIndex);
  syncEditingTestFromDom();

  if (action === "add-option") {
    state.editingTest.questions[questionIndex].options.push(makeEmptyOption("", false));
  }
  if (action === "remove-option") {
    const optionIndex = Number(button.dataset.optionIndex);
    if (state.editingTest.questions[questionIndex].options.length <= 2) {
      showNotice("Вопрос должен содержать минимум два варианта ответа.", "error");
      return;
    }
    state.editingTest.questions[questionIndex].options.splice(optionIndex, 1);
    if (!state.editingTest.questions[questionIndex].options.some((item) => item.is_correct)) {
      state.editingTest.questions[questionIndex].options[0].is_correct = true;
    }
  }
  if (action === "remove-question") {
    if (state.editingTest.questions.length <= 1) {
      showNotice("В тесте должен остаться хотя бы один вопрос.", "error");
      return;
    }
    state.editingTest.questions.splice(questionIndex, 1);
  }
  renderTestEditor();
});

elements.testEditorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    syncEditingTestFromDom();
    validateEditableTest(state.editingTest);

    if (state.editingTest.id) {
      const updated = await api(`/tests/${state.editingTest.id}`, {
        method: "PUT",
        body: JSON.stringify(state.editingTest),
      });
      state.editingTest = updated;
      showNotice("Тест обновлен.");
    } else {
      const created = await api("/tests", {
        method: "POST",
        body: JSON.stringify(state.editingTest),
      });
      state.editingTest = created;
      showNotice("Тест создан.");
    }

    renderTestEditor();
    await loadTests();
  } catch (error) {
    showNotice(error.message, "error");
  }
});

elements.teacherTestsList.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) {
    return;
  }
  const testId = Number(button.dataset.id);
  const action = button.dataset.action;

  try {
    if (action === "edit-test") {
      const test = await api(`/tests/${testId}`);
      state.editingTest = test;
      renderTestEditor();
      return;
    }

    if (action === "toggle-publish") {
      const nextPublished = button.dataset.published !== "true";
      await api(`/tests/${testId}/publish`, {
        method: "POST",
        body: JSON.stringify({ is_published: nextPublished }),
      });
      showNotice(nextPublished ? "Тест опубликован." : "Тест снят с публикации.");
      await loadTests();
      return;
    }

    if (action === "view-attempts") {
      state.selectedTeacherTestId = testId;
      await loadTeacherAttempts(testId);
      return;
    }

    if (action === "delete-test") {
      if (!window.confirm("Удалить тест вместе с вопросами и попытками?")) {
        return;
      }
      await api(`/tests/${testId}`, { method: "DELETE" });
      if (state.editingTest?.id === testId) {
        state.editingTest = makeEmptyTest();
        renderTestEditor();
      }
      if (state.selectedTeacherTestId === testId) {
        state.selectedTeacherTestId = null;
        elements.teacherAttempts.innerHTML = `<div class="empty-state">Выберите тест, чтобы увидеть попытки.</div>`;
        elements.teacherAttempts.dataset.count = "0";
      }
      showNotice("Тест удален.");
      await loadTests();
    }
  } catch (error) {
    showNotice(error.message, "error");
  }
});

elements.studentTestsList.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button || button.dataset.action !== "open-student-test") {
    return;
  }

  const testId = Number(button.dataset.id);
  try {
    const test = await api(`/tests/${testId}`);
    state.selectedStudentTest = test;
    renderStudentTestDetail(test);
  } catch (error) {
    showNotice(error.message, "error");
  }
});

resetUserForm();
state.editingTest = makeEmptyTest();
renderTestEditor();
elements.teacherAttempts.innerHTML = `<div class="empty-state">Выберите тест, чтобы увидеть попытки.</div>`;
elements.teacherAttempts.dataset.count = "0";
render();
restoreSession();
