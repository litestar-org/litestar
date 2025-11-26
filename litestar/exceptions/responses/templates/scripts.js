const expanders = document.querySelectorAll(".frame .expander");

for (const expander of expanders) {
  expander.addEventListener("click", (evt) => {
    const currentSnippet = evt.currentTarget.closest(".frame");
    const snippetWrapper = currentSnippet.querySelector(
      ".code-snippet-wrapper",
    );
    if (currentSnippet.classList.contains("collapsed")) {
      snippetWrapper.style.height = `${snippetWrapper.scrollHeight}px`;
      currentSnippet.classList.remove("collapsed");
    } else {
      currentSnippet.classList.add("collapsed");
      snippetWrapper.style.height = "0px";
    }
  });
}

// init height for non-collapsed code snippets so animation will be show
// their first collapse
const nonCollapsedSnippets = document.querySelectorAll(
  ".frame:not(.collapsed) .code-snippet-wrapper",
);

for (const snippet of nonCollapsedSnippets) {
  snippet.style.height = `${snippet.scrollHeight}px`;
}

function toggleTracebackView() {
  const browser = document.getElementById("browserTraceback");
  const pastebin = document.getElementById("pastebinTraceback");
  const toggleBtn = document.getElementById("toggleView");
  const copyBtn = document.getElementById("copyBtn");

  if (pastebin.style.display === "none") {
    browser.style.display = "none";
    pastebin.style.display = "block";
    copyBtn.style.display = "inline-block";
    toggleBtn.textContent = "Switch back to interactive view";
  } else {
    browser.style.display = "block";
    pastebin.style.display = "none";
    copyBtn.style.display = "none";
    toggleBtn.textContent = "Switch to copy-and-paste view";
  }
}

async function copyTraceback() {
  const textarea = document.getElementById("traceback_area");
  const copyBtn = document.getElementById("copyBtn");
  try {
    await navigator.clipboard.writeText(textarea.value);
    const original = copyBtn.textContent;
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = original), 2000);
  } catch (err) {
    textarea.select();
    document.execCommand("copy");
  }
}
