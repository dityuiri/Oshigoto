// Drag-to-reorder lists, X icon / TuneCore auto-fill, image previews, confirms.
(function () {
  // ---- reorder: [data-reorder=<POST url>] > .row[data-id]
  document.querySelectorAll("[data-reorder]").forEach(list => {
    let dragged = null;
    list.addEventListener("dragstart", e => {
      dragged = e.target.closest(".row");
      dragged?.classList.add("drag");
    });
    list.addEventListener("dragover", e => {
      e.preventDefault();
      const over = e.target.closest(".row");
      list.querySelectorAll(".over").forEach(r => r.classList.remove("over"));
      if (over && over !== dragged) over.classList.add("over");
    });
    list.addEventListener("drop", async e => {
      e.preventDefault();
      const over = e.target.closest(".row");
      list.querySelectorAll(".over").forEach(r => r.classList.remove("over"));
      if (!dragged || !over || over === dragged) return;
      list.insertBefore(dragged, over);
      dragged.classList.remove("drag");
      const ids = [...list.querySelectorAll(".row")].map(r => +r.dataset.id);
      await fetch(list.dataset.reorder, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ids }),
      });
      // numbering (and who is メイン / 2人目) depends on groups, so let the server redo it
      if (list.querySelector(".num")) location.reload();
    });
    list.addEventListener("dragend", () => dragged?.classList.remove("drag"));
  });

  // ---- auto-fill helpers on the edit form
  const form = document.querySelector("form.fields");
  const status = document.querySelector(".fetch-status");
  function say(text, bad) {
    if (!status) return;
    status.hidden = false;
    status.textContent = text;
    status.classList.toggle("bad", !!bad);
  }
  function setImage(field, url) {
    const box = document.querySelector(`[data-image-field="${field}"]`);
    if (!box || !url) return;
    box.querySelector(`input[name="${field}__url"]`).value = url;
    const img = box.querySelector(".preview");
    img.src = url;
    img.hidden = false;
  }
  function fillIfEmpty(name, value) {
    const el = form?.elements[name];
    if (el && !el.value && value) el.value = value;
  }
  async function getJSON(url) {
    const r = await fetch(url);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || "取得できませんでした");
    return data;
  }

  document.querySelectorAll("[data-fetch-x]").forEach(btn => btn.addEventListener("click", async () => {
    const input = btn.parentElement.querySelector("input");
    say("取得中…");
    try {
      const d = await getJSON("/admin/api/x-profile?handle=" + encodeURIComponent(input.value));
      input.value = d.handle;
      setImage(btn.dataset.image, d.icon_url);
      fillIfEmpty(btn.dataset.name, d.name);
      say(`取得しました: ${d.name}。保存するとアイコンがサーバーに保存されます。`);
    } catch (e) { say(e.message, true); }
  }));

  function setValue(name, value) {
    const el = form?.elements[name];
    if (el) el.value = value || "";
  }

  // 配信リンク: TuneCore / Spotify / Apple Music / YouTube Music. A TuneCore album
  // comes back with its track list; picking a track fills that song's details.
  document.querySelectorAll("[data-fetch-song]").forEach(btn => btn.addEventListener("click", async () => {
    const input = btn.parentElement.querySelector("input");
    const pick = btn.closest("label").querySelector(".track-pick");
    pick.hidden = true;
    say("取得中…");
    try {
      const d = await getJSON("/admin/api/song-link?url=" + encodeURIComponent(input.value));
      setImage(btn.dataset.image, d.image);
      fillIfEmpty("year", d.year);
      if (d.tracks.length) {
        pick.innerHTML = "";
        pick.add(new Option(`「${d.title}」から曲を選んでください (${d.tracks.length}曲)`, ""));
        d.tracks.forEach((t, i) => pick.add(new Option(`${t.no}. ${t.title}${t.lyrics_url ? "  · 歌詞あり" : ""}`, i)));
        pick.onchange = () => {
          const t = d.tracks[pick.value];
          if (!t) return;
          setValue("title_ja", t.title);
          setValue("title_romaji", t.title_romaji);
          setValue("lyrics_url", t.lyrics_url);
          say(`「${t.title}」を入力しました。${t.lyrics_url ? "歌詞ページも入れました。" : "この曲は歌詞ページがありません。"}`);
        };
        pick.hidden = false;
        say("アルバムです。下のリストから曲を選んでください。");
        return;
      }
      fillIfEmpty("title_ja", d.title);
      fillIfEmpty("title_romaji", d.title_romaji);
      fillIfEmpty("lyrics_url", d.lyrics_url);
      const note = d.service === "spotify" ? "Spotify はローマ字のタイトルしか返さないので、日本語タイトルは直してください。"
                                           : "タイトルは必要に応じて直してください。";
      say(`取得しました: ${d.title || "(タイトルなし)"}。${note}`);
    } catch (e) { say(e.message, true); }
  }));

  // preview a pasted image link (the server downloads it on save)
  document.querySelectorAll('.image input[type="url"]').forEach(inp => inp.addEventListener("input", () => {
    const img = inp.closest(".image").querySelector(".preview");
    const url = inp.value.trim();
    if (/^https?:\/\//.test(url)) { img.src = url; img.hidden = false; }
  }));

  // local preview when a file is picked
  document.querySelectorAll('.image input[type="file"]').forEach(inp => inp.addEventListener("change", () => {
    const file = inp.files[0];
    const img = inp.closest(".image").querySelector(".preview");
    if (file) { img.src = URL.createObjectURL(file); img.hidden = false; }
  }));

  document.querySelectorAll("form[data-confirm]").forEach(f => f.addEventListener("submit", e => {
    if (!confirm(f.dataset.confirm)) e.preventDefault();
  }));
  document.querySelectorAll("form[data-busy]").forEach(f => f.addEventListener("submit", () => {
    const b = f.querySelector("button");
    b.disabled = true;
    b.textContent = f.dataset.busy;
  }));
})();
