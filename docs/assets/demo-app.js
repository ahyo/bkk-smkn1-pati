/* ==========================================================================
   Demo statis BKK SMK Negeri 1 Pati (GitHub Pages)
   Seluruh data disimpan di localStorage peramban pengunjung — tidak ada server.
   Struktur halaman & kelas CSS sengaja dibuat identik dengan versi FastAPI
   agar penyesuaian tampilan di sini langsung dapat dipindahkan ke produksi.
   ========================================================================== */
(function () {
  "use strict";

  var KEY = "bkk_demo_state_v3";
  var SEK = "bkk_demo_session_v3";
  var SEKOLAH = "SMK Negeri 1 Pati";
  var DB, session;

  // ── Penyimpanan ─────────────────────────────────────────────────────────
  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      var parsed = raw ? JSON.parse(raw) : null;
      DB = parsed && parsed.version === window.SEED.version ? parsed : clone(window.SEED);
    } catch (e) { DB = clone(window.SEED); }
    try { session = JSON.parse(localStorage.getItem(SEK) || "null"); } catch (e) { session = null; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(DB)); } catch (e) {}
  }
  function setSession(userId) {
    session = userId ? { userId: userId } : null;
    try {
      if (session) localStorage.setItem(SEK, JSON.stringify(session));
      else localStorage.removeItem(SEK);
    } catch (e) {}
  }
  function resetDemo() {
    DB = clone(window.SEED); save(); setSession(null);
    flash("Data demo dikembalikan ke kondisi awal.", "info");
    go("#/");
  }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  // ── Util ────────────────────────────────────────────────────────────────
  var BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
               "Agustus", "September", "Oktober", "November", "Desember"];
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function nl2br(s) { return esc(s).replace(/\n/g, "<br>"); }
  function tgl(iso) {
    if (!iso) return "-";
    var d = new Date(String(iso).replace(" ", "T"));
    if (isNaN(d)) return "-";
    return d.getDate() + " " + BULAN[d.getMonth() + 1] + " " + d.getFullYear();
  }
  function tglJam(iso) {
    if (!iso) return "-";
    var d = new Date(String(iso).replace(" ", "T"));
    if (isNaN(d)) return "-";
    return tgl(iso) + " · " + String(d.getHours()).padStart(2, "0") + "." + String(d.getMinutes()).padStart(2, "0");
  }
  function rp(v) { return v == null ? "-" : "Rp" + Math.round(v).toLocaleString("id-ID"); }
  function gaji(j) {
    if (j.hidden || (!j.min && !j.max)) return "Negosiasi";
    if (j.min && j.max) return rp(j.min) + " – " + rp(j.max);
    return rp(j.min || j.max);
  }
  function inisial(nama) {
    return (nama || "?").split(/\s+/).filter(Boolean).slice(0, 2)
      .map(function (w) { return w[0].toUpperCase(); }).join("") || "?";
  }
  function today() { return new Date("2026-08-26"); }
  function expired(j) { return !!(j.deadline && new Date(j.deadline) < today()); }
  function nextId(arr) { return arr.reduce(function (m, x) { return Math.max(m, x.id || 0); }, 0) + 1; }

  // ── Pencarian entitas ───────────────────────────────────────────────────
  function user() { return session ? DB.users.find(function (u) { return u.id === session.userId; }) : null; }
  function company(id) { return DB.companies.find(function (c) { return c.id === id; }); }
  function myCompany() { var u = user(); return u && u.companyId ? company(u.companyId) : null; }
  function seeker(id) { return DB.seekers.find(function (s) { return s.id === id; }); }
  function mySeeker() { var u = user(); return u && u.seekerId ? seeker(u.seekerId) : null; }
  function seekerUser(sid) { return DB.users.find(function (u) { return u.seekerId === sid; }); }
  function job(id) { return DB.jobs.find(function (j) { return j.id === id; }); }
  function jobBySlug(slug) { return DB.jobs.find(function (j) { return j.slug === slug; }); }
  function appsOfJob(id) { return DB.applications.filter(function (a) { return a.jobId === id; }); }
  function publicJobs() {
    return DB.jobs.filter(function (j) {
      var c = company(j.companyId);
      return j.status === "published" && c && c.status === "verified" && !expired(j);
    });
  }
  function completeness(s) {
    var f = [s.phone, s.gender, s.birth, s.city, s.major, s.grad, s.headline, s.summary,
             s.skills, s.education, s.cv, s.photo, s.experience];
    return Math.round(f.filter(Boolean).length / f.length * 100);
  }

  // ── Flash ───────────────────────────────────────────────────────────────
  var pending = [];
  function flash(msg, cat) { pending.push({ message: msg, category: cat || "info" }); }
  function takeFlash() { var f = pending; pending = []; return f; }

  // ── Badge ───────────────────────────────────────────────────────────────
  var BADGE_APP = { submitted: "info", reviewed: "info", shortlisted: "warn", interview: "warn",
                    accepted: "ok", rejected: "danger", withdrawn: "muted" };
  var BADGE_JOB = { draft: "muted", pending: "warn", published: "ok", rejected: "danger", closed: "muted" };
  var BADGE_CO = { pending: "warn", verified: "ok", rejected: "danger", suspended: "muted" };

  // ── Navigasi ────────────────────────────────────────────────────────────
  function go(hash) {
    if (location.hash === hash) render();
    else location.hash = hash;
  }

  // ── Komponen ────────────────────────────────────────────────────────────
  function jobCard(j) {
    var c = company(j.companyId);
    return '<article class="job-card">' +
      '<div class="logo-box">' + esc(inisial(c.name)) + '</div>' +
      '<div class="job-main">' +
        '<div class="job-head">' +
          '<h3><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a></h3>' +
          '<span class="job-type">' + esc(DB.employment[j.type]) + '</span>' +
        '</div>' +
        '<div class="job-company"><a href="#/mitra/' + esc(c.slug) + '">' + esc(c.name) + '</a>' +
          (c.status === "verified"
            ? '<span class="verified-mark" title="Perusahaan terverifikasi BKK">' + ICON('verified') + '</span>'
            : "") + '</div>' +
        '<div class="job-meta">' +
          '<span>' + ICON('pin') + ' ' + esc(j.location) + (j.remote ? " · Remote" : "") + '</span>' +
          (j.major ? '<span>' + ICON('cap') + ' ' + esc(j.major) + '</span>' : "") +
          '<span>' + ICON('users') + ' ' + j.quota + ' posisi</span>' +
        '</div>' +
        '<div class="job-salary">' + esc(gaji(j)) + '</div>' +
        '<div class="job-foot">' +
          '<div class="chips">' +
            '<span class="chip">' + ICON('clock') + ' ' + (j.deadline ? "Tutup " + tgl(j.deadline) : "Tanpa batas waktu") + '</span>' +
            '<span class="chip">' + ICON('eye') + ' ' + (j.views || 0) + ' dilihat</span>' +
            '<span class="chip">' + ICON('inbox') + ' ' + appsOfJob(j.id).length + ' pelamar</span>' +
          '</div>' +
          '<a href="#/lowongan/' + esc(j.slug) + '" class="btn btn-outline btn-sm">Lihat Detail ' + ICON('arrow-right', 'xs') + '</a>' +
        '</div>' +
      '</div></article>';
  }

  function statCard(label, value, hint, mod) {
    return '<div class="stat ' + (mod || "") + '"><div class="label">' + esc(label) + '</div>' +
      '<div class="value">' + esc(value) + '</div>' +
      (hint ? '<div class="hint">' + esc(hint) + '</div>' : "") + '</div>';
  }

  function empty(ico, judul, pesan, url, label) {
    return '<div class="empty"><div class="ico">' + ICON(ico, "2xl") + '</div><h3>' + esc(judul) + '</h3>' +
      '<p>' + esc(pesan) + '</p>' +
      (url ? '<a href="' + url + '" class="btn btn-primary mt-1">' + esc(label) + '</a>' : "") + '</div>';
  }

  function tabs(items, aktif) {
    return '<div class="tabs">' + items.map(function (it) {
      return '<a href="' + it.href + '" class="' + (it.key === aktif ? "active" : "") + '">' + esc(it.label) + '</a>';
    }).join("") + '</div>';
  }

  function sidebar(role, path) {
    var groups;
    if (role === "seeker") {
      groups = [["Pencari Kerja", [
        ["#/pelamar", "target", "Ringkasan"], ["#/pelamar/lamaran", "inbox", "Lamaran Saya"],
        ["#/pelamar/tersimpan", "bookmark", "Tersimpan"], ["#/pelamar/profil", "user", "Profil & CV"]]],
        ["Jelajahi", [["#/lowongan", "search", "Cari Lowongan"], ["#/mitra", "building", "Perusahaan Mitra"]]]];
    } else if (role === "company") {
      groups = [["Perusahaan", [
        ["#/perusahaan", "chart", "Ringkasan"], ["#/perusahaan/lowongan", "clipboard", "Lowongan Saya"],
        ["#/perusahaan/pelamar", "users", "Pelamar"], ["#/perusahaan/profil", "building", "Profil Perusahaan"]]],
        ["Aksi Cepat", [["#/perusahaan/lowongan/baru", "plus", "Pasang Lowongan"], ["#/lowongan", "search", "Portal Publik"]]]];
    } else {
      groups = [["Panel Admin BKK", [
        ["#/admin", "shield", "Ringkasan"], ["#/admin/perusahaan", "building", "Perusahaan"],
        ["#/admin/lowongan", "clipboard", "Lowongan"], ["#/admin/lamaran", "inbox", "Lamaran"],
        ["#/admin/pengguna", "users", "Pengguna"]]],
        ["Pelaporan", [["#/admin/laporan", "chart", "Laporan & Rekap"],
        ["#/admin/pengumuman", "megaphone", "Pengumuman"], ["#/admin/log", "history", "Log Aktivitas"]]]];
    }
    return groups.map(function (g) {
      return '<div class="sidebar-label">' + esc(g[0]) + '</div><nav>' + g[1].map(function (it) {
        var aktif = it[0] === "#/" + path.join("/") || (it[0] === "#" + location.hash.slice(1).split("?")[0]);
        return '<a href="' + it[0] + '" class="' + (location.hash.split("?")[0] === it[0] ? "active" : "") + '">' +
          ICON(it[1], "md", "ico") + ' ' + esc(it[2]) + '</a>';
      }).join("") + '</nav>';
    }).join("");
  }

  function dashboardShell(role, path, main) {
    return '<div class="layout-side"><aside class="sidebar">' + sidebar(role, path) +
      '</aside><div>' + main + '</div></div>';
  }

  function timeline(status) {
    var urutan = ["submitted", "reviewed", "shortlisted", "interview", "accepted"];
    var pos = urutan.indexOf(status);
    return '<ul class="timeline">' + urutan.map(function (k, i) {
      var cls = i < pos ? "done" : (i === pos ? "current" : "");
      return '<li class="' + cls + '"><b>' + esc(DB.appStatus[k]) + '</b></li>';
    }).join("") + '</ul>';
  }

  // ── Halaman publik ──────────────────────────────────────────────────────
  function pageBeranda() {
    var jobs = publicJobs().slice(0, 6);
    var stats = {
      lowongan: publicJobs().length,
      perusahaan: DB.companies.filter(function (c) { return c.status === "verified"; }).length,
      pelamar: DB.seekers.length,
      penempatan: DB.applications.filter(function (a) { return a.status === "accepted"; }).length
    };
    var perJurusan = {};
    publicJobs().forEach(function (j) { perJurusan[j.major || "Umum"] = (perJurusan[j.major || "Umum"] || 0) + 1; });

    return '<section class="hero"><div class="container">' +
      '<span class="eyebrow">' + ICON('cap') + ' Portal Resmi BKK ' + SEKOLAH + '</span>' +
      '<h1>Temukan Karier Pertamamu Bersama Mitra Industri Sekolah</h1>' +
      '<p class="lead">Semua lowongan di portal ini diverifikasi terlebih dahulu oleh pengelola BKK sekolah, ' +
      'sehingga alumni terhindar dari informasi kerja palsu.</p>' +
      '<form class="search-bar" data-form="cari-beranda">' +
        '<input type="search" name="q" placeholder="Posisi, kata kunci, atau perusahaan">' +
        '<input type="text" name="lokasi" placeholder="Kota / kabupaten">' +
        '<select name="jurusan"><option value="">Semua Kompetensi Keahlian</option>' +
        DB.majors.map(function (m) { return '<option>' + esc(m) + '</option>'; }).join("") + '</select>' +
        '<button class="btn btn-accent" type="submit">' + ICON('search') + ' Cari Lowongan</button>' +
      '</form>' +
      '<div class="hero-stats">' +
        '<div><b>' + stats.lowongan + '</b><span>Lowongan aktif</span></div>' +
        '<div><b>' + stats.perusahaan + '</b><span>Perusahaan mitra</span></div>' +
        '<div><b>' + stats.pelamar + '</b><span>Pencari kerja terdaftar</span></div>' +
        '<div><b>' + stats.penempatan + '</b><span>Alumni tersalurkan</span></div>' +
      '</div></div></section>' +

      '<section class="section" style="padding-bottom:0"><div class="container"><div class="grid grid-3">' +
      DB.announcements.filter(function (a) { return a.published; }).slice(0, 3).map(function (a) {
        return '<div class="card"><div class="card-body"><span class="badge accent">' + ICON('megaphone') + ' Pengumuman</span>' +
          '<h3 class="mt-1">' + esc(a.title) + '</h3>' +
          '<p class="small muted">' + esc(a.body.slice(0, 160)) + (a.body.length > 160 ? "…" : "") + '</p>' +
          '<small class="muted">' + tgl(a.created) + '</small></div></div>';
      }).join("") + '</div></div></section>' +

      '<section class="section"><div class="container">' +
      '<div class="section-head"><div><span class="eyebrow-dark">Lowongan Terbaru</span>' +
      '<h2>Peluang kerja yang baru dibuka</h2>' +
      '<p>Diperbarui setiap kali mitra industri mengirimkan permintaan tenaga kerja.</p></div>' +
      '<a href="#/lowongan" class="btn btn-outline">Lihat Semua Lowongan ' + ICON('arrow-right', 'xs') + '</a></div>' +
      (jobs.length ? '<div class="grid grid-2">' + jobs.map(jobCard).join("") + '</div>'
                   : '<div class="card">' + empty("folder", "Belum ada lowongan tayang", "Silakan periksa kembali nanti.") + '</div>') +
      '</div></section>' +

      '<section class="section" style="background:var(--surface);border-block:1px solid var(--line)"><div class="container">' +
      '<div class="section-head"><div><span class="eyebrow-dark">Berdasarkan Jurusan</span>' +
      '<h2>Lowongan sesuai kompetensi keahlian</h2></div></div><div class="chips">' +
      Object.keys(perJurusan).map(function (m) {
        return '<a class="chip" href="#/lowongan?jurusan=' + encodeURIComponent(m) + '">' + ICON('cap') + ' ' + esc(m) +
          ' <b>' + perJurusan[m] + '</b></a>';
      }).join("") + '</div></div></section>' +

      '<section class="section"><div class="container">' +
      '<div class="section-head"><div><span class="eyebrow-dark">Alur Layanan</span>' +
      '<h2>Tiga langkah menuju penempatan kerja</h2></div></div><div class="grid grid-3">' +
      [["1️⃣", "Daftar & lengkapi profil", "Alumni membuat akun, mengisi data diri, kompetensi, dan mengunggah CV."],
       ["2️⃣", "Lamar lowongan terverifikasi", "Pilih lowongan sesuai jurusan, kirim lamaran, pantau statusnya."],
       ["3️⃣", "Seleksi & penempatan", "Perusahaan menyeleksi berkas, menjadwalkan wawancara, BKK mencatat hasilnya."]]
      .map(function (s) {
        return '<div class="card"><div class="card-body"><div style="font-size:1.8rem">' + s[0] + '</div>' +
          '<h3>' + esc(s[1]) + '</h3><p class="small muted">' + esc(s[2]) + '</p></div></div>';
      }).join("") + '</div></div></section>' +

      '<section class="section"><div class="container"><div class="card" ' +
      'style="background:linear-gradient(135deg,var(--brand-900),var(--brand-600));border:0">' +
      '<div class="card-body flex between items-center wrap gap"><div style="color:#fff">' +
      '<h2 style="color:#fff">Perusahaan? Pasang lowongan gratis.</h2>' +
      '<p style="color:#cfe0f3;margin:0;max-width:52ch">Daftarkan perusahaan Anda, tunggu verifikasi pengelola BKK, ' +
      'lalu publikasikan kebutuhan tenaga kerja langsung ke lulusan ' + SEKOLAH + '.</p></div>' +
      '<a href="#/masuk" class="btn btn-accent btn-lg">Coba Akun Perusahaan</a>' +
      '</div></div></div></section>';
  }

  function pageLowongan(qs) {
    var f = {
      q: qs.get("q") || "", lokasi: qs.get("lokasi") || "",
      jurusan: qs.get("jurusan") || "", tipe: qs.get("tipe") || "", urut: qs.get("urut") || "terbaru"
    };
    var list = publicJobs().filter(function (j) {
      var c = company(j.companyId);
      if (f.q) {
        var t = (j.title + " " + j.desc + " " + c.name).toLowerCase();
        if (t.indexOf(f.q.toLowerCase()) === -1) return false;
      }
      if (f.lokasi && j.location.toLowerCase().indexOf(f.lokasi.toLowerCase()) === -1) return false;
      if (f.jurusan && j.major !== f.jurusan) return false;
      if (f.tipe && j.type !== f.tipe) return false;
      return true;
    });
    if (f.urut === "gaji") list.sort(function (a, b) { return (b.max || 0) - (a.max || 0); });
    else if (f.urut === "deadline") list.sort(function (a, b) { return String(a.deadline || "9999").localeCompare(String(b.deadline || "9999")); });
    else list.sort(function (a, b) { return String(b.published || "").localeCompare(String(a.published || "")); });

    return '<div class="page-head"><div>' +
      '<div class="breadcrumb"><a href="#/">Beranda</a> › Lowongan</div>' +
      '<h1>Daftar Lowongan Kerja</h1><p>' + list.length + ' lowongan aktif terverifikasi pengelola BKK.</p></div></div>' +
      '<div class="filter-bar"><form data-form="filter-lowongan">' +
      '<div><label class="label">Kata kunci</label><input type="search" name="q" value="' + esc(f.q) + '" placeholder="Posisi / perusahaan"></div>' +
      '<div><label class="label">Lokasi</label><input type="text" name="lokasi" value="' + esc(f.lokasi) + '" placeholder="Semua kota"></div>' +
      '<div><label class="label">Kompetensi keahlian</label><select name="jurusan"><option value="">Semua jurusan</option>' +
      DB.majors.map(function (m) { return '<option ' + (f.jurusan === m ? "selected" : "") + '>' + esc(m) + '</option>'; }).join("") +
      '</select></div>' +
      '<div><label class="label">Tipe kerja</label><select name="tipe"><option value="">Semua tipe</option>' +
      Object.keys(DB.employment).map(function (k) {
        return '<option value="' + k + '" ' + (f.tipe === k ? "selected" : "") + '>' + esc(DB.employment[k]) + '</option>';
      }).join("") + '</select></div>' +
      '<div><label class="label">Urutkan</label><select name="urut">' +
      [["terbaru", "Terbaru"], ["gaji", "Gaji tertinggi"], ["deadline", "Segera ditutup"]].map(function (o) {
        return '<option value="' + o[0] + '" ' + (f.urut === o[0] ? "selected" : "") + '>' + o[1] + '</option>';
      }).join("") + '</select></div>' +
      '<div class="btn-group"><button class="btn btn-primary" type="submit">Terapkan</button>' +
      '<a href="#/lowongan" class="btn btn-ghost">Reset</a></div></form></div>' +
      (list.length ? '<div class="grid">' + list.map(jobCard).join("") + '</div>'
        : '<div class="card">' + empty("search", "Tidak ada lowongan yang cocok",
            "Coba ubah kata kunci atau longgarkan filter.", "#/lowongan", "Reset Pencarian") + '</div>');
  }

  function pageLowonganDetail(slug) {
    var j = jobBySlug(slug);
    if (!j) return pageError(404, "Lowongan tidak ditemukan.");
    var c = company(j.companyId);
    var u = user(), s = mySeeker();
    var sudah = s && DB.applications.some(function (a) { return a.jobId === j.id && a.seekerId === s.id; });
    var tersimpan = s && DB.saved.some(function (x) { return x.jobId === j.id && x.seekerId === s.id; });
    var related = publicJobs().filter(function (x) {
      return x.id !== j.id && (x.major === j.major || x.companyId === j.companyId);
    }).slice(0, 4);

    var aksi;
    if (!u) {
      aksi = '<p class="small muted">Masuk sebagai pencari kerja untuk mengirim lamaran.</p>' +
        '<a href="#/masuk" class="btn btn-primary btn-block">Masuk untuk Melamar</a>';
    } else if (u.role === "seeker") {
      if (sudah) {
        aksi = '<div class="alert alert-success mb-2"><span>' + ICON('verified') + '</span><span>Anda sudah melamar pada lowongan ini.</span></div>' +
          '<a href="#/pelamar/lamaran" class="btn btn-outline btn-block">Lihat Status Lamaran</a>';
      } else if (expired(j)) {
        aksi = '<div class="alert alert-danger mb-2"><span>' + ICON('alert') + '</span><span>Batas akhir lamaran sudah lewat.</span></div>';
      } else {
        aksi = '<h3>Kirim Lamaran</h3><form data-form="lamar" data-id="' + j.id + '">' +
          '<div class="field"><label>Surat lamaran singkat</label>' +
          '<textarea name="cover" maxlength="1500" placeholder="Perkenalkan diri Anda dan jelaskan mengapa cocok untuk posisi ini…"></textarea></div>' +
          '<div class="field"><label>Lampirkan CV</label><input type="file" name="cv" accept=".pdf,.doc,.docx">' +
          '<div class="help">' + (s && s.cv ? "CV tersimpan akan dipakai bila dikosongkan." : "Format PDF/DOC/DOCX.") + '</div></div>' +
          '<button class="btn btn-primary btn-block" type="submit">' + ICON('inbox') + ' Kirim Lamaran</button></form>';
      }
      aksi += '<button class="btn btn-ghost btn-block mt-1" data-action="toggle-simpan" data-id="' + j.id + '">' +
        (tersimpan ? ICON('bookmark') + " Hapus dari tersimpan" : ICON('bookmark') + " Simpan lowongan") + '</button>';
    } else if (u.role === "company") {
      aksi = '<p class="small muted">Anda masuk sebagai perusahaan.</p>' +
        '<a href="#/perusahaan/pelamar" class="btn btn-primary btn-block">Lihat Pelamar (' + appsOfJob(j.id).length + ')</a>' +
        (u.companyId === j.companyId ? '<a href="#/perusahaan/lowongan/' + j.id + '" class="btn btn-outline btn-block mt-1">Ubah Lowongan</a>' : "");
    } else {
      aksi = '<p class="small muted">Mode admin — pemantauan lowongan.</p>' +
        '<a href="#/admin/lowongan" class="btn btn-primary btn-block">Kelola di Panel Admin</a>';
    }

    function baris(l, v) { return '<div><small class="muted">' + l + '</small><div class="strong">' + v + '</div></div>'; }

    return '<div class="breadcrumb"><a href="#/">Beranda</a> › <a href="#/lowongan">Lowongan</a> › ' + esc(j.title) + '</div>' +
      (j.status !== "published" ? '<div class="alert alert-warning"><span>' + ICON('warning') + '</span><span>Pratinjau: lowongan ini berstatus <b>' +
        esc(DB.jobStatus[j.status]) + '</b> dan belum tampil untuk publik.</span></div>' : "") +
      '<div class="layout-side-r"><div>' +
      '<div class="card mb-3"><div class="card-body">' +
      '<div class="flex gap items-center wrap"><div class="logo-box" style="width:64px;height:64px">' + esc(inisial(c.name)) + '</div>' +
      '<div style="flex:1;min-width:200px"><h1 style="font-size:1.6rem;margin-bottom:.2rem">' + esc(j.title) + '</h1>' +
      '<div class="job-company"><a href="#/mitra/' + esc(c.slug) + '">' + esc(c.name) + '</a>' +
      (c.status === "verified" ? ' <span class="badge ok badge-dot">Terverifikasi</span>' : "") + '</div></div></div>' +
      '<div class="grid grid-2 mt-3">' +
        baris("Lokasi penempatan", ICON('pin') + " " + esc(j.location) + (j.remote ? " · Remote" : "")) +
        baris("Tipe pekerjaan", ICON('briefcase') + " " + esc(DB.employment[j.type])) +
        baris("Estimasi gaji", '<span style="color:var(--ok-700)">' + ICON('money') + ' ' + esc(gaji(j)) + '</span>') +
        baris("Kuota", ICON('users') + " " + j.quota + " orang") +
        baris("Jurusan dibutuhkan", ICON('cap') + " " + esc(j.major || "Semua jurusan")) +
        baris("Batas lamaran", ICON('clock') + " " + (j.deadline ? tgl(j.deadline) : "Tidak ditentukan")) +
        baris("Pendidikan minimal", ICON('book') + " SMK/SMA Sederajat") +
        baris("Ketentuan lain", esc(j.gender || "Semua") + (j.maxAge ? " · maks. " + j.maxAge + " tahun" : "")) +
      '</div></div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Deskripsi Pekerjaan</h2></div>' +
      '<div class="card-body prose">' + nl2br(j.desc) + '</div></div>' +
      (j.req ? '<div class="card mb-3"><div class="card-head"><h2>Kualifikasi &amp; Persyaratan</h2></div>' +
        '<div class="card-body prose">' + nl2br(j.req) + '</div></div>' : "") +
      (j.benefit ? '<div class="card mb-3"><div class="card-head"><h2>Fasilitas &amp; Benefit</h2></div>' +
        '<div class="card-body prose">' + nl2br(j.benefit) + '</div></div>' : "") +
      (related.length ? '<h2 class="mt-4 mb-2">Lowongan serupa</h2><div class="grid">' + related.map(jobCard).join("") + '</div>' : "") +
      '</div><aside><div class="card mb-2" style="position:sticky;top:82px"><div class="card-body">' + aksi +
      '<div class="divider"></div><div class="small muted">' +
      '<div class="flex between"><span>Pelamar saat ini</span><b>' + appsOfJob(j.id).length + '</b></div>' +
      '<div class="flex between"><span>Dilihat</span><b>' + (j.views || 0) + '</b></div>' +
      '<div class="flex between"><span>Diposting</span><b>' + tgl(j.published || j.deadline) + '</b></div>' +
      '</div></div></div>' +
      '<div class="card"><div class="card-body"><h3>Tentang perusahaan</h3>' +
      '<p class="small muted">' + esc((c.desc || "").slice(0, 260)) + '</p>' +
      '<div class="small"><div>' + ICON('factory') + ' ' + esc(c.industry) + '</div><div>' + ICON('pin') + ' ' + esc(c.city) + '</div></div>' +
      '<a href="#/mitra/' + esc(c.slug) + '" class="btn btn-outline btn-sm btn-block mt-2">Profil Perusahaan</a>' +
      '</div></div></aside></div>';
  }

  function pageMitra(qs) {
    var q = qs.get("q") || "";
    var list = DB.companies.filter(function (c) {
      return c.status === "verified" &&
        (!q || (c.name + c.industry + c.city).toLowerCase().indexOf(q.toLowerCase()) !== -1);
    });
    return '<div class="page-head"><div>' +
      '<div class="breadcrumb"><a href="#/">Beranda</a> › Perusahaan Mitra</div>' +
      '<h1>Perusahaan Mitra BKK</h1><p>' + list.length + ' dunia usaha &amp; dunia industri yang bekerja sama dengan ' + SEKOLAH + '.</p></div>' +
      '<form class="flex gap-sm" data-form="cari-mitra"><input type="search" name="q" value="' + esc(q) + '" placeholder="Cari nama / bidang / kota">' +
      '<button class="btn btn-primary" type="submit">Cari</button></form></div>' +
      (list.length ? '<div class="grid grid-3">' + list.map(function (c) {
        var n = publicJobs().filter(function (j) { return j.companyId === c.id; }).length;
        return '<div class="card"><div class="card-body">' +
          '<div class="flex gap-sm items-center mb-2"><div class="logo-box">' + esc(inisial(c.name)) + '</div>' +
          '<div style="min-width:0"><h3 class="truncate" style="margin:0"><a href="#/mitra/' + esc(c.slug) + '">' + esc(c.name) + '</a></h3>' +
          '<small class="muted">' + esc(c.industry) + '</small></div></div>' +
          '<div class="small muted">' + ICON('pin') + ' ' + esc(c.city) + '</div>' +
          '<div class="job-foot"><span class="badge ok">' + n + ' lowongan aktif</span>' +
          '<a href="#/mitra/' + esc(c.slug) + '" class="btn btn-ghost btn-sm">Detail ' + ICON('arrow-right', 'xs') + '</a></div></div></div>';
      }).join("") + '</div>' : '<div class="card">' + empty("building", "Tidak ada perusahaan", "Coba kata kunci lain.") + '</div>');
  }

  function pageMitraDetail(slug) {
    var c = DB.companies.find(function (x) { return x.slug === slug; });
    if (!c || c.status !== "verified") return pageError(404, "Perusahaan mitra tidak ditemukan.");
    var jobs = publicJobs().filter(function (j) { return j.companyId === c.id; });
    return '<div class="breadcrumb"><a href="#/">Beranda</a> › <a href="#/mitra">Perusahaan Mitra</a> › ' + esc(c.name) + '</div>' +
      '<div class="card mb-3"><div class="card-body flex gap items-center wrap">' +
      '<div class="logo-box" style="width:96px;height:96px;font-size:1.6rem">' + esc(inisial(c.name)) + '</div>' +
      '<div style="flex:1;min-width:220px"><h1 style="margin-bottom:.25rem">' + esc(c.name) + '</h1>' +
      '<div class="chips"><span class="badge ok badge-dot">Mitra Terverifikasi</span>' +
      '<span class="chip">' + ICON('factory') + ' ' + esc(c.industry) + '</span><span class="chip">' + ICON('pin') + ' ' + esc(c.city) + '</span>' +
      '<span class="chip">' + ICON('users') + ' ' + esc(c.employees) + ' karyawan</span></div></div></div></div>' +
      '<div class="layout-side-r"><div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Profil Perusahaan</h2></div>' +
      '<div class="card-body prose">' + nl2br(c.desc) + '</div></div>' +
      '<h2 class="mb-2">Lowongan aktif (' + jobs.length + ')</h2>' +
      (jobs.length ? '<div class="grid">' + jobs.map(jobCard).join("") + '</div>'
        : '<div class="card">' + empty("inbox", "Belum ada lowongan aktif", "Perusahaan ini sedang tidak membuka lowongan.") + '</div>') +
      '</div><aside><div class="card"><div class="card-head"><h3>Informasi Kontak</h3></div>' +
      '<div class="card-body small"><p>' + ICON('pin') + ' ' + esc(c.address) + '</p><p>' + ICON('phone') + ' ' + esc(c.phone) + '</p>' +
      '<p>' + ICON('user') + ' ' + esc(c.pic) + '</p><p class="muted">Bergabung sejak ' + tgl(c.joined) + '</p>' +
      '<div class="divider"></div><p class="tiny muted">Pengelola BKK tidak memungut biaya apa pun dalam proses rekrutmen.</p>' +
      '</div></div></aside></div>';
  }

  function pageTentang() {
    return '<div class="page-head"><div><div class="breadcrumb"><a href="#/">Beranda</a> › Tentang</div>' +
      '<h1>Tentang Bursa Kerja Khusus</h1><p>Unit layanan penempatan kerja di bawah ' + SEKOLAH + '.</p></div></div>' +
      '<div class="grid grid-4 mb-3">' +
      statCard("Lowongan aktif", publicJobs().length) +
      statCard("Perusahaan mitra", DB.companies.filter(function (c) { return c.status === "verified"; }).length, "", "ok") +
      statCard("Pencari kerja", DB.seekers.length, "", "accent") +
      statCard("Biaya layanan", "Rp0", "Gratis untuk alumni", "warn") + '</div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Apa itu BKK?</h2></div><div class="card-body prose">' +
      '<p>Bursa Kerja Khusus (BKK) adalah lembaga yang dibentuk di satuan pendidikan kejuruan sebagai unit pelaksana ' +
      'yang memberikan pelayanan dan informasi lowongan kerja, pelaksana pemasaran, penyaluran, serta penempatan ' +
      'tenaga kerja bagi lulusan sekolah yang bersangkutan.</p>' +
      '<h4>Tugas pokok</h4><p>Mendata lulusan, menjalin kerja sama dengan dunia usaha dan dunia industri (DUDI), ' +
      'menyalurkan lulusan sesuai kompetensi keahlian, serta melakukan penelusuran alumni yang telah bekerja.</p></div></div>' +
      '<div class="card"><div class="card-head"><h2>Alur pelayanan</h2></div><div class="card-body"><ul class="timeline">' +
      [["Perusahaan mendaftar", "Mengisi profil dan data legalitas perusahaan pada portal."],
       ["Verifikasi oleh admin BKK", "Pengelola memeriksa keabsahan perusahaan sebelum akun diaktifkan."],
       ["Perusahaan memasang lowongan", "Lowongan diperiksa admin agar informasi tidak menyesatkan."],
       ["Alumni melamar", "Pencari kerja mengirim lamaran beserta CV melalui dashboard."],
       ["Seleksi & penempatan", "Perusahaan memperbarui status; BKK merekap hasil penyaluran."]]
      .map(function (s, i, arr) {
        return '<li class="' + (i === arr.length - 1 ? "current" : "done") + '"><b>' + esc(s[0]) + '</b><small>' + esc(s[1]) + '</small></li>';
      }).join("") + '</ul></div></div>';
  }

  function pageMasuk() {
    var akun = [
      { id: 1, ico: "shield", label: "Admin BKK", desc: "Verifikasi mitra, moderasi lowongan, dan rekap penyaluran.", email: "admin@bkksmkn1pati.sch.id" },
      { id: 2, ico: "building", label: "Perusahaan", desc: "Pasang lowongan dan seleksi pelamar (PT Dua Kelinci).", email: "hrd@ptduakelinci.co.id" },
      { id: 10, ico: "cap", label: "Pencari Kerja", desc: "Kelola CV, lamar lowongan, pantau seleksi (Aditya Nugroho).", email: "aditya.nugroho@gmail.com" }
    ];
    return '<div class="center mb-3"><span class="eyebrow-dark">Mode Demo</span>' +
      '<h1>Masuk sebagai peran mana?</h1>' +
      '<p class="muted">Demo ini tidak memverifikasi kata sandi — pilih salah satu akan langsung masuk ke dashboard peran tersebut.</p></div>' +
      '<div class="grid grid-3" style="max-width:1000px;margin:0 auto">' +
      akun.map(function (a) {
        return '<div class="role-card"><div class="ico">' + ICON(a.ico, "3xl") + '</div><h2>' + esc(a.label) + '</h2>' +
          '<p class="small muted">' + esc(a.desc) + '</p>' +
          '<p class="tiny muted"><code>' + esc(a.email) + '</code></p>' +
          '<button class="btn btn-primary btn-block" data-action="login" data-id="' + a.id + '">Masuk sebagai ' + esc(a.label) + '</button></div>';
      }).join("") + '</div>' +
      '<div class="card mt-4" style="max-width:820px;margin:2rem auto 0"><div class="card-body">' +
      '<h3>Catatan untuk peninjau</h3><p class="small muted mb-0">Pada aplikasi produksi (FastAPI + PostgreSQL), halaman ini ' +
      'berupa formulir email dan kata sandi dengan hash bcrypt, sesi cookie tertandatangani, serta pembatasan akses per peran. ' +
      'Demo ini hanya meniru alur antarmukanya agar dapat ditinjau tanpa memasang server.</p></div></div>';
  }

  function pageError(code, detail) {
    return '<div class="card" style="max-width:620px;margin:3rem auto"><div class="card-body center">' +
      '<div style="font-size:3.4rem;line-height:1">' + ICON('search') + '</div><h1 style="font-size:2.6rem;margin:.3rem 0">' + code + '</h1>' +
      '<p class="muted">' + esc(detail) + '</p>' +
      '<a href="#/" class="btn btn-primary mt-2">Kembali ke Beranda</a></div></div>';
  }

  // ── Dashboard pencari kerja ─────────────────────────────────────────────
  function seekerApps(s) {
    return DB.applications.filter(function (a) { return a.seekerId === s.id; })
      .sort(function (a, b) { return String(b.created).localeCompare(String(a.created)); });
  }

  function pageSeekerDashboard() {
    var s = mySeeker(), u = user();
    var apps = seekerApps(s);
    var proses = apps.filter(function (a) { return ["reviewed", "shortlisted", "interview"].indexOf(a.status) !== -1; }).length;
    var diterima = apps.filter(function (a) { return a.status === "accepted"; }).length;
    var tersimpan = DB.saved.filter(function (x) { return x.seekerId === s.id; }).length;
    var sudahIds = apps.map(function (a) { return a.jobId; });
    var rec = publicJobs().filter(function (j) { return sudahIds.indexOf(j.id) === -1 && j.major === s.major; });
    if (rec.length < 4) rec = rec.concat(publicJobs().filter(function (j) {
      return sudahIds.indexOf(j.id) === -1 && rec.indexOf(j) === -1;
    })).slice(0, 4);

    var c = completeness(s);
    return '<div class="page-head"><div><h1>Halo, ' + esc(u.name.split(" ")[0]) + ' </h1>' +
      '<p>Ringkasan aktivitas pencarian kerja Anda.</p></div>' +
      '<a href="#/lowongan" class="btn btn-primary">' + ICON('search') + ' Cari Lowongan</a></div>' +
      (c < 80 ? '<div class="card mb-3" style="border-color:var(--warn-500)"><div class="card-body">' +
        '<div class="flex between items-center wrap gap"><div style="flex:1;min-width:240px">' +
        '<h3 class="mb-1">Lengkapi profil Anda (' + c + '%)</h3>' +
        '<p class="small muted mb-2">Profil lengkap membuat perusahaan lebih mudah menilai kompetensi Anda.</p>' +
        '<div class="progress"><span style="width:' + c + '%"></span></div></div>' +
        '<a href="#/pelamar/profil" class="btn btn-accent">Lengkapi Sekarang</a></div></div></div>' : "") +
      '<div class="grid grid-4 mb-3">' +
      statCard("Total lamaran", apps.length) + statCard("Dalam proses", proses, "", "warn") +
      statCard("Diterima", diterima, "", "ok") + statCard("Tersimpan", tersimpan, "", "accent") + '</div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Lamaran terakhir</h2>' +
      '<a href="#/pelamar/lamaran" class="btn btn-ghost btn-sm">Semua lamaran ' + ICON('arrow-right', 'xs') + '</a></div>' +
      (apps.length ? '<div class="table-wrap"><table class="data"><thead><tr>' +
        '<th>Posisi</th><th>Perusahaan</th><th>Dikirim</th><th>Status</th></tr></thead><tbody>' +
        apps.slice(0, 5).map(function (a) {
          var j = job(a.jobId);
          return '<tr><td><a class="cell-main" href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a>' +
            '<div class="cell-sub">' + ICON('pin') + ' ' + esc(j.location) + '</div></td>' +
            '<td>' + esc(company(j.companyId).name) + '</td><td class="nowrap">' + tgl(a.created) + '</td>' +
            '<td><span class="badge ' + BADGE_APP[a.status] + '">' + esc(DB.appStatus[a.status]) + '</span></td></tr>';
        }).join("") + '</tbody></table></div>'
        : empty("inbox", "Belum ada lamaran", "Mulai lamar lowongan yang sesuai kompetensi Anda.", "#/lowongan", "Cari Lowongan")) +
      '</div>' +
      '<div class="card"><div class="card-head"><h2>Rekomendasi untuk Anda</h2>' +
      '<span class="badge muted">' + esc(s.major || "Semua jurusan") + '</span></div>' +
      '<div class="card-body">' + (rec.length ? '<div class="grid">' + rec.slice(0, 4).map(jobCard).join("") + '</div>'
        : '<p class="muted center">Belum ada lowongan baru yang cocok.</p>') + '</div></div>';
  }

  function pageSeekerLamaran(qs) {
    var s = mySeeker(), f = qs.get("status") || "";
    var apps = seekerApps(s).filter(function (a) { return !f || a.status === f; });
    var items = [{ key: "", label: "Semua", href: "#/pelamar/lamaran" }].concat(
      Object.keys(DB.appStatus).map(function (k) {
        return { key: k, label: DB.appStatus[k], href: "#/pelamar/lamaran?status=" + k };
      }));

    return '<div class="page-head"><div><h1>Lamaran Saya</h1><p>' + apps.length + ' lamaran pada filter ini.</p></div></div>' +
      tabs(items, f) +
      (apps.length ? '<div class="grid">' + apps.map(function (a) {
        var j = job(a.jobId), c = company(j.companyId);
        return '<div class="card"><div class="card-body">' +
          '<div class="flex between items-center wrap gap"><div style="flex:1;min-width:230px">' +
          '<h3 style="margin-bottom:.15rem"><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a></h3>' +
          '<div class="job-company">' + esc(c.name) + '</div>' +
          '<div class="job-meta"><span>' + ICON('pin') + ' ' + esc(j.location) + '</span><span>' + ICON('briefcase') + ' ' + esc(DB.employment[j.type]) + '</span>' +
          '<span>' + ICON('history') + ' Dilamar ' + tgl(a.created) + '</span></div></div>' +
          '<div class="right"><span class="badge ' + BADGE_APP[a.status] + '">' + esc(DB.appStatus[a.status]) + '</span>' +
          '<div class="tiny muted mt-1">Diperbarui ' + tgl(a.updated) + '</div></div></div>' +
          (a.interview ? '<div class="alert alert-warning mt-2 mb-0"><span>' + ICON('calendar') + '</span><span>Jadwal wawancara: <b>' +
            tglJam(a.interview) + '</b></span></div>' : "") +
          (a.note ? '<div class="alert alert-info mt-2 mb-0"><span>' + ICON('message') + '</span><span>Catatan perusahaan: ' + esc(a.note) + '</span></div>' : "") +
          '<div class="job-foot"><div class="chips"><span class="chip">' + ICON('file') + ' CV terkirim</span>' +
          '<span class="chip">' + ICON('cap') + ' ' + esc(j.major || "Umum") + '</span></div>' +
          (["accepted", "rejected", "withdrawn"].indexOf(a.status) === -1 ?
            '<button class="btn btn-outline btn-sm" data-action="batal-lamaran" data-id="' + a.id + '">Batalkan lamaran</button>' : "") +
          '</div></div></div>';
      }).join("") + '</div>'
        : '<div class="card">' + empty("inbox", "Belum ada lamaran pada filter ini",
            "Ubah filter status atau kirim lamaran baru.", "#/lowongan", "Cari Lowongan") + '</div>');
  }

  function pageSeekerTersimpan() {
    var s = mySeeker();
    var list = DB.saved.filter(function (x) { return x.seekerId === s.id; })
      .map(function (x) { return job(x.jobId); }).filter(Boolean);
    return '<div class="page-head"><div><h1>Lowongan Tersimpan</h1>' +
      '<p>' + list.length + ' lowongan Anda tandai untuk dilamar nanti.</p></div></div>' +
      (list.length ? '<div class="grid">' + list.map(function (j) {
        return '<div>' + jobCard(j) +
          '<button class="btn btn-ghost btn-sm mt-1" data-action="toggle-simpan" data-id="' + j.id + '">' + ICON('trash') + ' Hapus dari tersimpan</button></div>';
      }).join("") + '</div>'
        : '<div class="card">' + empty("bookmark", "Belum ada lowongan tersimpan",
            'Klik "Simpan lowongan" pada halaman detail.', "#/lowongan", "Jelajahi Lowongan") + '</div>');
  }

  function pageSeekerProfil() {
    var s = mySeeker(), u = user(), c = completeness(s);
    function fld(label, name, val, type) {
      return '<div class="field"><label>' + label + '</label>' +
        '<input type="' + (type || "text") + '" name="' + name + '" value="' + esc(val || "") + '"></div>';
    }
    return '<div class="page-head"><div><h1>Profil &amp; CV</h1>' +
      '<p>Data ini yang dilihat perusahaan ketika Anda melamar.</p></div>' +
      '<div class="right"><div class="tiny muted">Kelengkapan profil</div>' +
      '<div class="strong" style="font-size:1.2rem">' + c + '%</div></div></div>' +
      '<div class="progress mb-3"><span style="width:' + c + '%"></span></div>' +
      '<form data-form="profil-pelamar">' +
      '<div class="card mb-3"><div class="card-head"><h2>Identitas</h2></div><div class="card-body">' +
      '<div class="flex gap items-center wrap mb-3"><div class="avatar avatar-xl">' + esc(inisial(u.name)) + '</div>' +
      '<div style="flex:1;min-width:220px"><label>Foto profil</label><input type="file" name="photo" accept="image/*">' +
      '<div class="help">JPG/PNG, maksimal 5 MB.</div></div></div>' +
      fld("Nama lengkap", "name", u.name) +
      '<div class="form-row-3">' + fld("NIS / NISN", "nis", s.nis) + fld("Nomor WhatsApp", "phone", s.phone, "tel") +
      '<div class="field"><label>Jenis kelamin</label><select name="gender">' +
      ["", "L", "P"].map(function (g) {
        return '<option value="' + g + '" ' + (s.gender === g ? "selected" : "") + '>' +
          (g === "L" ? "Laki-laki" : g === "P" ? "Perempuan" : "— pilih —") + '</option>';
      }).join("") + '</select></div></div>' +
      '<div class="form-row">' + fld("Tanggal lahir", "birth", s.birth, "date") + fld("Domisili (kota)", "city", s.city) + '</div>' +
      '</div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Pendidikan &amp; Kompetensi</h2></div><div class="card-body">' +
      '<div class="form-row"><div class="field"><label>Kompetensi keahlian</label><select name="major">' +
      '<option value="">— pilih —</option>' + DB.majors.map(function (m) {
        return '<option ' + (s.major === m ? "selected" : "") + '>' + esc(m) + '</option>';
      }).join("") + '</select></div>' + fld("Tahun lulus", "grad", s.grad, "number") + '</div>' +
      fld("Headline profil", "headline", s.headline) +
      '<div class="field"><label>Ringkasan diri</label><textarea name="summary" maxlength="1200">' + esc(s.summary || "") + '</textarea></div>' +
      fld("Keahlian (pisahkan dengan koma)", "skills", s.skills) +
      '<div class="field"><label>Riwayat pendidikan</label><textarea name="education">' + esc(s.education || "") + '</textarea></div>' +
      '<div class="field"><label>Pengalaman kerja / PKL</label><textarea name="experience">' + esc(s.experience || "") + '</textarea></div>' +
      '</div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Dokumen &amp; Status</h2></div><div class="card-body">' +
      '<div class="field"><label>Curriculum Vitae (CV)</label><input type="file" name="cv" accept=".pdf,.doc,.docx">' +
      '<div class="help">' + (s.cv ? "CV sudah terunggah — unggah baru untuk mengganti." : "Belum ada CV.") + '</div></div>' +
      '<label class="check"><input type="checkbox" name="openToWork" ' + (s.openToWork ? "checked" : "") + '>' +
      '<span>Saya sedang terbuka untuk peluang kerja.</span></label></div>' +
      '<div class="card-foot flex between items-center wrap gap">' +
      '<small class="muted">Perubahan langsung berlaku pada lamaran berikutnya.</small>' +
      '<button class="btn btn-primary" type="submit">' + ICON('save') + ' Simpan Profil</button></div></div></form>';
  }

  // ── Dashboard perusahaan ────────────────────────────────────────────────
  function myJobs() { var c = myCompany(); return DB.jobs.filter(function (j) { return j.companyId === c.id; }); }
  function myApps() {
    var ids = myJobs().map(function (j) { return j.id; });
    return DB.applications.filter(function (a) { return ids.indexOf(a.jobId) !== -1; })
      .sort(function (a, b) { return String(b.created).localeCompare(String(a.created)); });
  }

  function pageCompanyDashboard() {
    var c = myCompany(), jobs = myJobs(), apps = myApps();
    var byStatus = {};
    apps.forEach(function (a) { byStatus[a.status] = (byStatus[a.status] || 0) + 1; });
    var tayang = jobs.filter(function (j) { return j.status === "published"; });
    var views = jobs.reduce(function (m, j) { return m + (j.views || 0); }, 0);
    var total = apps.length || 1;

    return '<div class="page-head"><div><h1>' + esc(c.name) + '</h1>' +
      '<p>Ringkasan rekrutmen melalui BKK ' + SEKOLAH + '.</p></div>' +
      '<a href="#/perusahaan/lowongan/baru" class="btn btn-primary">' + ICON('plus') + ' Pasang Lowongan</a></div>' +
      (c.status !== "verified" ? '<div class="alert alert-warning mb-3"><span>' + ICON('clock') + '</span><span>Status akun: <b>' +
        esc(DB.companyStatus[c.status]) + '</b>. ' + esc(c.note || "Pengelola BKK sedang memverifikasi data perusahaan Anda.") +
        '</span></div>' : "") +
      '<div class="grid grid-4 mb-3">' +
      statCard("Lowongan tayang", tayang.length, jobs.filter(function (j) { return j.status === "pending"; }).length + " menunggu persetujuan") +
      statCard("Total pelamar", apps.length, (byStatus.submitted || 0) + " lamaran baru", "accent") +
      statCard("Diterima", byStatus.accepted || 0, "", "ok") +
      statCard("Total dilihat", views, "akumulasi semua lowongan", "warn") + '</div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Pelamar terbaru</h2>' +
      '<a href="#/perusahaan/pelamar" class="btn btn-ghost btn-sm">Semua pelamar ' + ICON('arrow-right', 'xs') + '</a></div>' +
      (apps.length ? '<div class="table-wrap"><table class="data"><thead><tr>' +
        '<th>Pelamar</th><th>Posisi dilamar</th><th>Jurusan</th><th>Tanggal</th><th>Status</th><th></th></tr></thead><tbody>' +
        apps.slice(0, 6).map(function (a) {
          var s = seeker(a.seekerId), su = seekerUser(s.id), j = job(a.jobId);
          return '<tr><td><div class="flex gap-sm items-center"><span class="avatar">' + esc(inisial(su.name)) + '</span>' +
            '<div><div class="cell-main">' + esc(su.name) + '</div><div class="cell-sub">' + esc(s.headline || su.email) + '</div></div></div></td>' +
            '<td>' + esc(j.title) + '</td><td class="cell-sub">' + esc(s.major) + '</td>' +
            '<td class="nowrap cell-sub">' + tgl(a.created) + '</td>' +
            '<td><span class="badge ' + BADGE_APP[a.status] + '">' + esc(DB.appStatus[a.status]) + '</span></td>' +
            '<td class="right"><a class="btn btn-outline btn-sm" href="#/perusahaan/pelamar/' + a.id + '">Tinjau</a></td></tr>';
        }).join("") + '</tbody></table></div>'
        : empty("users", "Belum ada pelamar", "Pelamar akan muncul setelah lowongan Anda tayang.")) + '</div>' +
      '<div class="grid grid-2"><div class="card"><div class="card-head"><h2>Lowongan aktif</h2>' +
      '<a href="#/perusahaan/lowongan" class="btn btn-ghost btn-sm">Kelola ' + ICON('arrow-right', 'xs') + '</a></div><div class="card-body">' +
      (tayang.length ? tayang.map(function (j) {
        return '<div class="flex between items-center gap" style="padding:.6rem 0;border-bottom:1px solid var(--line)">' +
          '<div style="min-width:0"><div class="cell-main truncate"><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a></div>' +
          '<div class="cell-sub">' + ICON('pin') + ' ' + esc(j.location) + ' · ' + ICON('clock') + ' ' + (j.deadline ? tgl(j.deadline) : "tanpa batas") + '</div></div>' +
          '<span class="badge info nowrap">' + appsOfJob(j.id).length + ' pelamar</span></div>';
      }).join("") : '<p class="muted center">Belum ada lowongan tayang.</p>') + '</div></div>' +
      '<div class="card"><div class="card-head"><h2>Corong seleksi</h2></div><div class="card-body">' +
      Object.keys(DB.appStatus).map(function (k) {
        var n = byStatus[k] || 0;
        return '<div class="hbar"><div><div class="flex between"><span>' + esc(DB.appStatus[k]) + '</span><b>' + n + '</b></div>' +
          '<div class="track"><i style="width:' + (n / total * 100).toFixed(1) + '%"></i></div></div>' +
          '<span class="tiny muted right">' + Math.round(n / total * 100) + '%</span></div>';
      }).join("") + '</div></div></div>';
  }

  function pageCompanyJobs(qs) {
    var f = qs.get("status") || "";
    var jobs = myJobs().filter(function (j) { return !f || j.status === f; });
    var items = [{ key: "", label: "Semua", href: "#/perusahaan/lowongan" }].concat(
      Object.keys(DB.jobStatus).map(function (k) {
        return { key: k, label: DB.jobStatus[k], href: "#/perusahaan/lowongan?status=" + k };
      }));

    return '<div class="page-head"><div><h1>Lowongan Saya</h1><p>' + jobs.length + ' lowongan pada filter ini.</p></div>' +
      '<a href="#/perusahaan/lowongan/baru" class="btn btn-primary">' + ICON('plus') + ' Pasang Lowongan</a></div>' + tabs(items, f) +
      (jobs.length ? '<div class="card"><div class="table-wrap"><table class="data"><thead><tr>' +
        '<th>Lowongan</th><th>Tipe</th><th>Kuota</th><th>Pelamar</th><th>Batas</th><th>Status</th><th></th></tr></thead><tbody>' +
        jobs.map(function (j) {
          return '<tr><td><div class="cell-main"><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a></div>' +
            '<div class="cell-sub">' + ICON('pin') + ' ' + esc(j.location) + ' · ' + ICON('cap') + ' ' + esc(j.major || "Umum") + ' · ' + ICON('eye') + ' ' + (j.views || 0) + '</div>' +
            (j.reviewNote ? '<div class="cell-sub" style="color:var(--danger-700)">' + ICON('message') + ' ' + esc(j.reviewNote) + '</div>' : "") + '</td>' +
            '<td class="cell-sub nowrap">' + esc(DB.employment[j.type]) + '</td><td>' + j.quota + '</td>' +
            '<td><span class="badge info">' + appsOfJob(j.id).length + '</span></td>' +
            '<td class="cell-sub nowrap">' + (j.deadline ? tgl(j.deadline) : "—") +
            (expired(j) ? '<div class="tiny" style="color:var(--danger-700)">kedaluwarsa</div>' : "") + '</td>' +
            '<td><span class="badge ' + BADGE_JOB[j.status] + '">' + esc(DB.jobStatus[j.status]) + '</span></td>' +
            '<td><div class="cell-actions"><a class="btn btn-outline btn-sm" href="#/perusahaan/lowongan/' + j.id + '">Ubah</a>' +
            (j.status === "published"
              ? '<button class="btn btn-ghost btn-sm" data-action="tutup-lowongan" data-id="' + j.id + '">Tutup</button>'
              : (appsOfJob(j.id).length === 0
                ? '<button class="btn btn-ghost btn-sm" data-action="hapus-lowongan" data-id="' + j.id + '">Hapus</button>' : "")) +
            '</div></td></tr>';
        }).join("") + '</tbody></table></div></div>'
        : '<div class="card">' + empty("clipboard", "Belum ada lowongan", "Buat lowongan pertama Anda.",
            "#/perusahaan/lowongan/baru", "Pasang Lowongan") + '</div>');
  }

  function pageCompanyJobForm(id) {
    var j = id ? job(Number(id)) : null;
    if (id && (!j || j.companyId !== myCompany().id)) return pageError(404, "Lowongan tidak ditemukan.");
    function v(k, d) { return j ? (j[k] == null ? (d || "") : j[k]) : (d || ""); }

    return '<div class="page-head"><div>' +
      '<div class="breadcrumb"><a href="#/perusahaan/lowongan">Lowongan Saya</a> › ' + (j ? "Ubah" : "Baru") + '</div>' +
      '<h1>' + (j ? "Ubah Lowongan" : "Pasang Lowongan Baru") + '</h1>' +
      '<p>Lowongan akan ditinjau admin BKK sebelum tayang di portal publik.</p></div>' +
      (j ? '<span class="badge ' + BADGE_JOB[j.status] + '">' + esc(DB.jobStatus[j.status]) + '</span>' : "") + '</div>' +
      '<form data-form="simpan-lowongan" data-id="' + (j ? j.id : "") + '">' +
      '<div class="card mb-3"><div class="card-head"><h2>Informasi Utama</h2></div><div class="card-body">' +
      '<div class="field"><label>Judul posisi <span class="req">*</span></label>' +
      '<input type="text" name="title" required value="' + esc(v("title")) + '" placeholder="mis. Operator Produksi"></div>' +
      '<div class="form-row-3"><div class="field"><label>Tipe pekerjaan</label><select name="type">' +
      Object.keys(DB.employment).map(function (k) {
        return '<option value="' + k + '" ' + (v("type", "full_time") === k ? "selected" : "") + '>' + esc(DB.employment[k]) + '</option>';
      }).join("") + '</select></div>' +
      '<div class="field"><label>Lokasi penempatan <span class="req">*</span></label>' +
      '<input type="text" name="location" required value="' + esc(v("location")) + '"></div>' +
      '<div class="field"><label>Jumlah dibutuhkan</label><input type="number" name="quota" min="1" value="' + esc(v("quota", 1)) + '"></div></div>' +
      '<label class="check"><input type="checkbox" name="remote" ' + (j && j.remote ? "checked" : "") + '>' +
      '<span>Pekerjaan dapat dilakukan jarak jauh (remote / hybrid).</span></label></div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Deskripsi &amp; Persyaratan</h2></div><div class="card-body">' +
      '<div class="field"><label>Deskripsi pekerjaan <span class="req">*</span></label>' +
      '<textarea name="desc" required style="min-height:160px">' + esc(v("desc")) + '</textarea></div>' +
      '<div class="field"><label>Kualifikasi &amp; persyaratan</label>' +
      '<textarea name="req" style="min-height:130px">' + esc(v("req")) + '</textarea></div>' +
      '<div class="field"><label>Fasilitas &amp; benefit</label>' +
      '<textarea name="benefit" style="min-height:100px">' + esc(v("benefit")) + '</textarea></div></div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Kriteria &amp; Kompensasi</h2></div><div class="card-body">' +
      '<div class="form-row"><div class="field"><label>Kompetensi keahlian yang dicari</label><select name="major">' +
      '<option value="">Semua jurusan</option>' + DB.majors.map(function (m) {
        return '<option ' + (v("major") === m ? "selected" : "") + '>' + esc(m) + '</option>';
      }).join("") + '</select></div>' +
      '<div class="field"><label>Batas akhir lamaran</label><input type="date" name="deadline" value="' + esc(v("deadline")) + '"></div></div>' +
      '<div class="form-row-3">' +
      '<div class="field"><label>Gaji minimum (Rp)</label><input type="number" name="min" value="' + esc(v("min")) + '"></div>' +
      '<div class="field"><label>Gaji maksimum (Rp)</label><input type="number" name="max" value="' + esc(v("max")) + '"></div>' +
      '<div class="field"><label>Usia maksimal</label><input type="number" name="maxAge" value="' + esc(v("maxAge")) + '"></div></div>' +
      '<label class="check"><input type="checkbox" name="hidden" ' + (j && j.hidden ? "checked" : "") + '>' +
      '<span>Sembunyikan nominal gaji (tampilkan sebagai "Negosiasi").</span></label></div>' +
      '<div class="card-foot flex between items-center wrap gap">' +
      '<a href="#/perusahaan/lowongan" class="btn btn-ghost">Batal</a>' +
      '<div class="btn-group"><button class="btn btn-outline" type="submit" name="aksi" value="draft">' + ICON('save') + ' Simpan sebagai draf</button>' +
      '<button class="btn btn-primary" type="submit" name="aksi" value="submit">' + ICON('send') + ' Kirim untuk ditinjau</button></div>' +
      '</div></div></form>';
  }

  function pageCompanyPelamar(qs) {
    var fj = qs.get("job") || "", fs = qs.get("status") || "", q = qs.get("q") || "";
    var apps = myApps().filter(function (a) {
      if (fj && String(a.jobId) !== fj) return false;
      if (fs && a.status !== fs) return false;
      if (q) {
        var s = seeker(a.seekerId), su = seekerUser(s.id);
        if ((su.name + s.major + s.skills).toLowerCase().indexOf(q.toLowerCase()) === -1) return false;
      }
      return true;
    });

    return '<div class="page-head"><div><h1>Pelamar</h1><p>' + apps.length + ' lamaran pada filter ini.</p></div></div>' +
      '<div class="filter-bar"><form data-form="filter-pelamar">' +
      '<div><label class="label">Lowongan</label><select name="job"><option value="">Semua lowongan</option>' +
      myJobs().map(function (j) {
        return '<option value="' + j.id + '" ' + (fj === String(j.id) ? "selected" : "") + '>' + esc(j.title) + '</option>';
      }).join("") + '</select></div>' +
      '<div><label class="label">Status seleksi</label><select name="status"><option value="">Semua status</option>' +
      Object.keys(DB.appStatus).map(function (k) {
        return '<option value="' + k + '" ' + (fs === k ? "selected" : "") + '>' + esc(DB.appStatus[k]) + '</option>';
      }).join("") + '</select></div>' +
      '<div><label class="label">Cari kandidat</label><input type="search" name="q" value="' + esc(q) + '" placeholder="Nama / jurusan / keahlian"></div>' +
      '<div class="btn-group"><button class="btn btn-primary" type="submit">Terapkan</button>' +
      '<a href="#/perusahaan/pelamar" class="btn btn-ghost">Reset</a></div></form></div>' +
      (apps.length ? '<div class="grid grid-2">' + apps.map(function (a) {
        var s = seeker(a.seekerId), su = seekerUser(s.id), j = job(a.jobId);
        var skills = (s.skills || "").split(",").map(function (x) { return x.trim(); }).filter(Boolean);
        return '<div class="card"><div class="card-body">' +
          '<div class="flex gap items-center mb-2"><span class="avatar avatar-lg">' + esc(inisial(su.name)) + '</span>' +
          '<div style="min-width:0;flex:1"><h3 class="truncate" style="margin:0">' + esc(su.name) + '</h3>' +
          '<div class="cell-sub truncate">' + esc(s.headline || s.major) + '</div>' +
          '<span class="badge ' + BADGE_APP[a.status] + ' mt-1">' + esc(DB.appStatus[a.status]) + '</span></div></div>' +
          '<div class="job-meta"><span>' + ICON('clipboard') + ' ' + esc(j.title) + '</span><span>' + ICON('cap') + ' ' + esc(s.major) + '</span>' +
          '<span>' + ICON('calendar') + ' Lulus ' + s.grad + '</span><span>' + ICON('pin') + ' ' + esc(s.city) + '</span></div>' +
          '<div class="chips mt-1">' + skills.slice(0, 4).map(function (x) { return '<span class="chip">' + esc(x) + '</span>'; }).join("") +
          (skills.length > 4 ? '<span class="chip">+' + (skills.length - 4) + '</span>' : "") + '</div>' +
          '<div class="job-foot"><small class="muted">Melamar ' + tgl(a.created) + '</small>' +
          '<a class="btn btn-primary btn-sm" href="#/perusahaan/pelamar/' + a.id + '">Tinjau ' + ICON('arrow-right', 'xs') + '</a></div></div></div>';
      }).join("") + '</div>'
        : '<div class="card">' + empty("users", "Belum ada pelamar pada filter ini", "Ubah filter pencarian.") + '</div>');
  }

  function pageCompanyPelamarDetail(id) {
    var a = DB.applications.find(function (x) { return x.id === Number(id); });
    if (!a) return pageError(404, "Data pelamar tidak ditemukan.");
    var j = job(a.jobId);
    if (j.companyId !== myCompany().id) return pageError(403, "Pelamar ini bukan untuk lowongan perusahaan Anda.");
    var s = seeker(a.seekerId), su = seekerUser(s.id);
    var skills = (s.skills || "").split(",").map(function (x) { return x.trim(); }).filter(Boolean);
    var riwayat = DB.applications.filter(function (x) { return x.seekerId === s.id && x.id !== a.id; });

    function baris(l, v) { return '<div><small class="muted">' + l + '</small><div class="strong">' + esc(v || "-") + '</div></div>'; }

    return '<div class="breadcrumb"><a href="#/perusahaan/pelamar">Pelamar</a> › ' + esc(su.name) + '</div>' +
      '<div class="layout-side-r"><div>' +
      '<div class="card mb-3"><div class="card-body flex gap items-center wrap">' +
      '<span class="avatar avatar-xl">' + esc(inisial(su.name)) + '</span>' +
      '<div style="flex:1;min-width:220px"><h1 style="margin-bottom:.15rem">' + esc(su.name) + '</h1>' +
      '<p class="muted mb-1">' + esc(s.headline) + '</p><div class="chips">' +
      '<span class="badge ' + BADGE_APP[a.status] + '">' + esc(DB.appStatus[a.status]) + '</span>' +
      '<span class="chip">' + ICON('cap') + ' ' + esc(s.major) + '</span><span class="chip">' + ICON('calendar') + ' Lulus ' + s.grad + '</span>' +
      (s.openToWork ? '<span class="badge ok">Terbuka untuk kerja</span>' : "") + '</div></div>' +
      (s.cv ? '<span class="btn btn-outline">' + ICON('file') + ' CV tersedia</span>' : '<span class="badge muted">Belum unggah CV</span>') + '</div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Melamar untuk</h2></div><div class="card-body">' +
      '<h3><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a></h3>' +
      '<div class="job-meta"><span>' + ICON('pin') + ' ' + esc(j.location) + '</span><span>' + ICON('briefcase') + ' ' + esc(DB.employment[j.type]) + '</span>' +
      '<span>' + ICON('history') + ' Dilamar ' + tgl(a.created) + '</span></div>' +
      (a.cover ? '<div class="divider"></div><h4>Surat lamaran</h4><div class="prose">' + nl2br(a.cover) + '</div>' : "") +
      '</div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Profil Kandidat</h2></div><div class="card-body">' +
      '<div class="grid grid-2 mb-2">' + baris("Email", su.email) + baris("Telepon", s.phone) +
      baris("Jenis kelamin", s.gender === "L" ? "Laki-laki" : "Perempuan") + baris("Tanggal lahir", tgl(s.birth)) +
      baris("Domisili", s.city) + baris("NIS / NISN", s.nis) + '</div>' +
      (skills.length ? '<h4>Keahlian</h4><div class="chips mb-2">' +
        skills.map(function (x) { return '<span class="chip">' + esc(x) + '</span>'; }).join("") + '</div>' : "") +
      (s.summary ? '<h4>Ringkasan</h4><div class="prose">' + nl2br(s.summary) + '</div>' : "") +
      (s.education ? '<h4>Pendidikan</h4><div class="prose">' + nl2br(s.education) + '</div>' : "") +
      (s.experience ? '<h4>Pengalaman</h4><div class="prose">' + nl2br(s.experience) + '</div>' : "") +
      '</div></div>' +
      (riwayat.length ? '<div class="card"><div class="card-head"><h2>Riwayat lamaran lain</h2></div><div class="card-body">' +
        riwayat.map(function (r) {
          return '<div class="flex between items-center" style="padding:.5rem 0;border-bottom:1px solid var(--line)">' +
            '<span>' + esc(job(r.jobId).title) + '</span>' +
            '<span class="badge ' + BADGE_APP[r.status] + '">' + esc(DB.appStatus[r.status]) + '</span></div>';
        }).join("") + '</div></div>' : "") +
      '</div><aside><div class="card" style="position:sticky;top:82px">' +
      '<div class="card-head"><h3>Perbarui Status Seleksi</h3></div><div class="card-body">' +
      '<form data-form="status-pelamar" data-id="' + a.id + '">' +
      '<div class="field"><label>Status</label><select name="status">' +
      Object.keys(DB.appStatus).filter(function (k) { return k !== "withdrawn"; }).map(function (k) {
        return '<option value="' + k + '" ' + (a.status === k ? "selected" : "") + '>' + esc(DB.appStatus[k]) + '</option>';
      }).join("") + '</select></div>' +
      '<div class="field"><label>Jadwal wawancara</label>' +
      '<input type="datetime-local" name="interview" value="' + esc((a.interview || "").replace(" ", "T")) + '"></div>' +
      '<div class="field"><label>Catatan untuk pelamar</label>' +
      '<textarea name="note" maxlength="600">' + esc(a.note || "") + '</textarea></div>' +
      '<button class="btn btn-primary btn-block" type="submit">Simpan Status</button></form>' +
      '<div class="divider"></div>' + timeline(a.status) + '</div></div></aside></div>';
  }

  function pageCompanyProfil() {
    var c = myCompany();
    function fld(label, name, val, type) {
      return '<div class="field"><label>' + label + '</label><input type="' + (type || "text") +
        '" name="' + name + '" value="' + esc(val || "") + '"></div>';
    }
    return '<div class="page-head"><div><h1>Profil Perusahaan</h1>' +
      '<p>Informasi ini tampil pada halaman mitra dan setiap lowongan Anda.</p></div>' +
      '<span class="badge ' + BADGE_CO[c.status] + '">' + esc(DB.companyStatus[c.status]) + '</span></div>' +
      (c.note ? '<div class="alert alert-info mb-3"><span>' + ICON('message') + '</span><span>Catatan admin BKK: ' + esc(c.note) + '</span></div>' : "") +
      '<form data-form="profil-perusahaan">' +
      '<div class="card mb-3"><div class="card-head"><h2>Identitas Perusahaan</h2></div><div class="card-body">' +
      '<div class="flex gap items-center wrap mb-3"><div class="logo-box" style="width:96px;height:96px;font-size:1.5rem">' +
      esc(inisial(c.name)) + '</div><div style="flex:1;min-width:220px"><label>Logo perusahaan</label>' +
      '<input type="file" name="logo" accept="image/*"><div class="help">JPG/PNG, rasio 1:1.</div></div></div>' +
      fld("Nama perusahaan", "name", c.name) +
      '<div class="form-row-3">' + fld("Bidang usaha", "industry", c.industry) + fld("Kota / kabupaten", "city", c.city) +
      fld("Jumlah karyawan", "employees", c.employees) + '</div>' +
      '<div class="field"><label>Alamat lengkap</label><textarea name="address">' + esc(c.address) + '</textarea></div>' +
      '<div class="field"><label>Deskripsi perusahaan</label>' +
      '<textarea name="desc" maxlength="2000" style="min-height:140px">' + esc(c.desc) + '</textarea></div></div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Kontak &amp; Penanggung Jawab</h2></div><div class="card-body">' +
      '<div class="form-row-3">' + fld("Nama PIC", "pic", c.pic) + fld("Telepon", "phone", c.phone, "tel") +
      fld("Situs web", "website", c.website, "url") + '</div></div>' +
      '<div class="card-foot flex between items-center wrap gap">' +
      (c.status === "verified" ? '<a href="#/mitra/' + esc(c.slug) + '" class="btn btn-ghost">' + ICON('eye') + ' Lihat halaman publik</a>'
        : '<small class="muted">Halaman publik aktif setelah akun terverifikasi.</small>') +
      '<button class="btn btn-primary" type="submit">' + ICON('save') + ' Simpan Profil</button></div></div></form>';
  }

  // ── Panel admin ─────────────────────────────────────────────────────────
  function pageAdminDashboard() {
    var lamaran = DB.applications.length;
    var diterima = DB.applications.filter(function (a) { return a.status === "accepted"; }).length;
    var pendingCo = DB.companies.filter(function (c) { return c.status === "pending"; });
    var pendingJob = DB.jobs.filter(function (j) { return j.status === "pending"; });

    var perBulan = {};
    DB.applications.forEach(function (a) {
      var m = String(a.created).slice(0, 7);
      perBulan[m] = (perBulan[m] || 0) + 1;
    });
    var bulanKeys = Object.keys(perBulan).sort().slice(-6);
    var maxB = Math.max.apply(null, bulanKeys.map(function (k) { return perBulan[k]; }).concat([1]));

    var perJurusan = {};
    DB.jobs.filter(function (j) { return j.status === "published"; })
      .forEach(function (j) { perJurusan[j.major || "Umum"] = (perJurusan[j.major || "Umum"] || 0) + 1; });
    var jurKeys = Object.keys(perJurusan).sort(function (a, b) { return perJurusan[b] - perJurusan[a]; });
    var maxJ = perJurusan[jurKeys[0]] || 1;

    return '<div class="page-head"><div><h1>Panel Pemantauan BKK</h1>' +
      '<p>Ringkasan seluruh aktivitas portal bursa kerja sekolah.</p></div>' +
      '<div class="btn-group"><a href="#/admin/laporan" class="btn btn-outline">' + ICON('chart') + ' Laporan</a>' +
      '<button class="btn btn-primary" data-action="ekspor" data-jenis="lamaran">' + ICON('download') + ' Ekspor CSV</button></div></div>' +
      (pendingCo.length || pendingJob.length ? '<div class="alert alert-warning mb-3"><span>' + ICON('clock') + '</span><span>Ada <b>' +
        pendingCo.length + '</b> perusahaan dan <b>' + pendingJob.length + '</b> lowongan menunggu tindakan Anda. ' +
        '<a href="#/admin/perusahaan?status=pending">Verifikasi perusahaan</a> · ' +
        '<a href="#/admin/lowongan?status=pending">Tinjau lowongan</a></span></div>' : "") +
      '<div class="grid grid-4 mb-3">' +
      statCard("Total pengguna", DB.users.length, DB.seekers.length + " pencari kerja") +
      statCard("Perusahaan mitra", DB.companies.filter(function (c) { return c.status === "verified"; }).length,
               "dari " + DB.companies.length + " terdaftar", "ok") +
      statCard("Lowongan tayang", DB.jobs.filter(function (j) { return j.status === "published"; }).length,
               "dari " + DB.jobs.length + " total", "accent") +
      statCard("Tingkat penerimaan", (lamaran ? (diterima / lamaran * 100).toFixed(1) : 0) + "%",
               diterima + " dari " + lamaran + " lamaran", "warn") + '</div>' +
      '<div class="grid grid-2 mb-3">' +
      '<div class="card"><div class="card-head"><h2>Antrean verifikasi perusahaan</h2>' +
      '<a href="#/admin/perusahaan?status=pending" class="btn btn-ghost btn-sm">Semua ' + ICON('arrow-right', 'xs') + '</a></div><div class="card-body">' +
      (pendingCo.length ? pendingCo.map(function (c) {
        return '<div class="flex between items-center gap" style="padding:.6rem 0;border-bottom:1px solid var(--line)">' +
          '<div style="min-width:0"><div class="cell-main truncate">' + esc(c.name) + '</div>' +
          '<div class="cell-sub">' + esc(c.industry) + ' · ' + esc(c.city) + ' · ' + tgl(c.joined) + '</div></div>' +
          '<button class="btn btn-ok btn-sm" data-action="verif-perusahaan" data-id="' + c.id + '" data-status="verified">Verifikasi</button></div>';
      }).join("") : '<p class="muted center mb-0">Tidak ada antrean. ' + ICON('check-circle') + '</p>') + '</div></div>' +
      '<div class="card"><div class="card-head"><h2>Lowongan menunggu persetujuan</h2>' +
      '<a href="#/admin/lowongan?status=pending" class="btn btn-ghost btn-sm">Semua ' + ICON('arrow-right', 'xs') + '</a></div><div class="card-body">' +
      (pendingJob.length ? pendingJob.map(function (j) {
        return '<div class="flex between items-center gap" style="padding:.6rem 0;border-bottom:1px solid var(--line)">' +
          '<div style="min-width:0"><div class="cell-main truncate">' + esc(j.title) + '</div>' +
          '<div class="cell-sub">' + esc(company(j.companyId).name) + ' · ' + ICON('pin') + ' ' + esc(j.location) + '</div></div>' +
          '<button class="btn btn-ok btn-sm" data-action="moderasi-lowongan" data-id="' + j.id + '" data-status="published">Setujui</button></div>';
      }).join("") : '<p class="muted center mb-0">Tidak ada antrean. ' + ICON('check-circle') + '</p>') + '</div></div></div>' +
      '<div class="grid grid-2 mb-3">' +
      '<div class="card"><div class="card-head"><h2>Tren lamaran masuk</h2><span class="badge muted">6 bulan terakhir</span></div>' +
      '<div class="card-body"><div class="bars">' + bulanKeys.map(function (k) {
        var n = perBulan[k];
        return '<div class="bar"><b>' + n + '</b><i style="height:' + (n / maxB * 100).toFixed(1) + '%"></i>' +
          '<small>' + BULAN[Number(k.slice(5))].slice(0, 3) + " " + k.slice(2, 4) + '</small></div>';
      }).join("") + '</div></div></div>' +
      '<div class="card"><div class="card-head"><h2>Lowongan per kompetensi keahlian</h2></div><div class="card-body">' +
      jurKeys.map(function (k) {
        return '<div class="hbar"><div><div class="flex between"><span class="truncate">' + esc(k) + '</span>' +
          '<b>' + perJurusan[k] + '</b></div><div class="track"><i style="width:' +
          (perJurusan[k] / maxJ * 100).toFixed(1) + '%"></i></div></div>' +
          '<span class="tiny muted right">' + perJurusan[k] + ' lowongan</span></div>';
      }).join("") + '</div></div></div>' +
      '<div class="card"><div class="card-head"><h2>Aktivitas terakhir</h2>' +
      '<a href="#/admin/log" class="btn btn-ghost btn-sm">Semua log ' + ICON('arrow-right', 'xs') + '</a></div>' +
      '<div class="table-wrap"><table class="data"><thead><tr><th>Waktu</th><th>Pelaku</th><th>Aksi</th><th>Keterangan</th></tr></thead><tbody>' +
      DB.logs.slice(0, 6).map(function (l) {
        return '<tr><td class="nowrap cell-sub">' + tglJam(l.at) + '</td><td>' + esc(l.actor) + '</td>' +
          '<td><span class="badge muted">' + esc(l.action) + '</span></td><td class="cell-sub">' + esc(l.detail) + '</td></tr>';
      }).join("") + '</tbody></table></div></div>';
  }

  function pageAdminPerusahaan(qs) {
    var f = qs.get("status") || "";
    var list = DB.companies.filter(function (c) { return !f || c.status === f; });
    var items = [{ key: "", label: "Semua", href: "#/admin/perusahaan" }].concat(
      Object.keys(DB.companyStatus).map(function (k) {
        return { key: k, label: DB.companyStatus[k], href: "#/admin/perusahaan?status=" + k };
      }));

    return '<div class="page-head"><div><h1>Kelola Perusahaan</h1><p>' + list.length + ' perusahaan pada filter ini.</p></div>' +
      '<button class="btn btn-outline" data-action="ekspor" data-jenis="perusahaan">' + ICON('download') + ' Ekspor CSV</button></div>' + tabs(items, f) +
      '<div class="grid">' + list.map(function (c) {
        var n = DB.jobs.filter(function (j) { return j.companyId === c.id; }).length;
        var cu = DB.users.find(function (u) { return u.companyId === c.id; });
        return '<div class="card"><div class="card-body">' +
          '<div class="flex gap items-center wrap"><div class="logo-box">' + esc(inisial(c.name)) + '</div>' +
          '<div style="flex:1;min-width:220px"><h3 style="margin-bottom:.15rem">' + esc(c.name) +
          ' <span class="badge ' + BADGE_CO[c.status] + '">' + esc(DB.companyStatus[c.status]) + '</span></h3>' +
          '<div class="cell-sub">' + ICON('factory') + ' ' + esc(c.industry) + ' · ' + ICON('pin') + ' ' + esc(c.city) + ' · ' + ICON('user') + ' ' + esc(c.pic) + '</div>' +
          '<div class="cell-sub">' + ICON('mail') + ' ' + esc(cu ? cu.email : "-") + ' · ' + ICON('phone') + ' ' + esc(c.phone) +
          ' · ' + ICON('clipboard') + ' ' + n + ' lowongan · ' + ICON('history') + ' daftar ' + tgl(c.joined) + '</div>' +
          (c.note ? '<div class="cell-sub" style="color:var(--warn-700)">' + ICON('message') + ' ' + esc(c.note) + '</div>' : "") +
          '</div></div><div class="job-foot"><div class="chips">' +
          (c.status === "verified" ? '<a class="chip" href="#/mitra/' + esc(c.slug) + '">' + ICON('eye') + ' Halaman publik</a>' : "") +
          '</div><form class="flex gap-sm wrap items-center" data-form="verif-perusahaan" data-id="' + c.id + '">' +
          '<input type="text" name="note" placeholder="Catatan verifikasi" value="' + esc(c.note || "") + '" style="width:230px">' +
          '<select name="status" style="width:auto">' + Object.keys(DB.companyStatus).map(function (k) {
            return '<option value="' + k + '" ' + (c.status === k ? "selected" : "") + '>' + esc(DB.companyStatus[k]) + '</option>';
          }).join("") + '</select>' +
          '<button class="btn btn-primary btn-sm" type="submit">Terapkan</button></form></div></div></div>';
      }).join("") + '</div>';
  }

  function pageAdminLowongan(qs) {
    var f = qs.get("status") || "";
    var list = DB.jobs.filter(function (j) { return !f || j.status === f; });
    var items = [{ key: "", label: "Semua", href: "#/admin/lowongan" }].concat(
      Object.keys(DB.jobStatus).map(function (k) {
        return { key: k, label: DB.jobStatus[k], href: "#/admin/lowongan?status=" + k };
      }));

    return '<div class="page-head"><div><h1>Moderasi Lowongan</h1><p>' + list.length + ' lowongan pada filter ini.</p></div>' +
      '<button class="btn btn-outline" data-action="ekspor" data-jenis="lowongan">' + ICON('download') + ' Ekspor CSV</button></div>' + tabs(items, f) +
      '<div class="grid">' + list.map(function (j) {
        var c = company(j.companyId);
        return '<div class="card"><div class="card-body">' +
          '<h3 style="margin-bottom:.15rem"><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a> ' +
          '<span class="badge ' + BADGE_JOB[j.status] + '">' + esc(DB.jobStatus[j.status]) + '</span></h3>' +
          '<div class="cell-sub">' + ICON('building') + ' ' + esc(c.name) + ' · ' + ICON('pin') + ' ' + esc(j.location) + ' · ' + ICON('cap') + ' ' + esc(j.major || "Umum") + '</div>' +
          '<div class="cell-sub">' + ICON('money') + ' ' + esc(gaji(j)) + ' · ' + ICON('users') + ' ' + j.quota + ' orang · ' + ICON('inbox') + ' ' + appsOfJob(j.id).length +
          ' pelamar · ' + ICON('eye') + ' ' + (j.views || 0) + ' · ' + ICON('clock') + ' ' + (j.deadline ? tgl(j.deadline) : "tanpa batas") + '</div>' +
          (j.reviewNote ? '<div class="cell-sub" style="color:var(--warn-700)">' + ICON('message') + ' ' + esc(j.reviewNote) + '</div>' : "") +
          '<div class="job-foot"><a class="btn btn-outline btn-sm" href="#/lowongan/' + esc(j.slug) + '">Tinjau isi lowongan</a>' +
          '<form class="flex gap-sm wrap items-center" data-form="moderasi-lowongan" data-id="' + j.id + '">' +
          '<input type="text" name="note" placeholder="Catatan untuk perusahaan" value="' + esc(j.reviewNote || "") + '" style="width:220px">' +
          '<select name="status" style="width:auto">' + Object.keys(DB.jobStatus).map(function (k) {
            return '<option value="' + k + '" ' + (j.status === k ? "selected" : "") + '>' + esc(DB.jobStatus[k]) + '</option>';
          }).join("") + '</select>' +
          '<button class="btn btn-primary btn-sm" type="submit">Terapkan</button></form></div></div></div>';
      }).join("") + '</div>';
  }

  function pageAdminLamaran(qs) {
    var f = qs.get("status") || "";
    var list = DB.applications.filter(function (a) { return !f || a.status === f; })
      .sort(function (a, b) { return String(b.created).localeCompare(String(a.created)); });
    var items = [{ key: "", label: "Semua", href: "#/admin/lamaran" }].concat(
      Object.keys(DB.appStatus).map(function (k) {
        return { key: k, label: DB.appStatus[k], href: "#/admin/lamaran?status=" + k };
      }));

    return '<div class="page-head"><div><h1>Pemantauan Lamaran</h1><p>' + list.length + ' lamaran pada filter ini.</p></div>' +
      '<button class="btn btn-outline" data-action="ekspor" data-jenis="lamaran">' + ICON('download') + ' Ekspor CSV</button></div>' + tabs(items, f) +
      '<div class="card"><div class="table-wrap"><table class="data"><thead><tr>' +
      '<th>Pelamar</th><th>Jurusan</th><th>Lowongan</th><th>Perusahaan</th><th>Tanggal</th><th>Status</th></tr></thead><tbody>' +
      (list.length ? list.map(function (a) {
        var s = seeker(a.seekerId), su = seekerUser(s.id), j = job(a.jobId);
        return '<tr><td><div class="cell-main">' + esc(su.name) + '</div>' +
          '<div class="cell-sub">' + esc(su.email) + ' · NIS ' + esc(s.nis) + '</div></td>' +
          '<td class="cell-sub">' + esc(s.major) + '<div class="tiny">lulus ' + s.grad + '</div></td>' +
          '<td><a href="#/lowongan/' + esc(j.slug) + '">' + esc(j.title) + '</a></td>' +
          '<td class="cell-sub">' + esc(company(j.companyId).name) + '</td>' +
          '<td class="nowrap cell-sub">' + tgl(a.created) + '</td>' +
          '<td><span class="badge ' + BADGE_APP[a.status] + '">' + esc(DB.appStatus[a.status]) + '</span></td></tr>';
      }).join("") : '<tr><td colspan="6" class="center muted">Belum ada lamaran pada filter ini.</td></tr>') +
      '</tbody></table></div></div>';
  }

  function pageAdminPengguna(qs) {
    var f = qs.get("role") || "";
    var list = DB.users.filter(function (u) { return !f || u.role === f; });
    var items = [
      { key: "", label: "Semua", href: "#/admin/pengguna" },
      { key: "seeker", label: "Pencari Kerja", href: "#/admin/pengguna?role=seeker" },
      { key: "company", label: "Perusahaan", href: "#/admin/pengguna?role=company" },
      { key: "admin", label: "Admin", href: "#/admin/pengguna?role=admin" }
    ];
    var LBL = { admin: "Admin", company: "Perusahaan", seeker: "Pencari Kerja" };
    var CLS = { admin: "accent", company: "info", seeker: "ok" };

    return '<div class="page-head"><div><h1>Kelola Pengguna</h1><p>' + list.length + ' akun pada filter ini.</p></div></div>' +
      tabs(items, f) +
      '<div class="card"><div class="table-wrap"><table class="data"><thead><tr>' +
      '<th>Pengguna</th><th>Peran</th><th>Detail</th><th>Terdaftar</th><th>Status</th><th></th></tr></thead><tbody>' +
      list.map(function (u) {
        var detail = "Administrator portal";
        if (u.role === "company") {
          var c = company(u.companyId);
          detail = esc(c.industry) + " · " + esc(c.city) + '<br><span class="badge ' + BADGE_CO[c.status] + '">' +
            esc(DB.companyStatus[c.status]) + '</span>';
        } else if (u.role === "seeker") {
          var s = seeker(u.seekerId);
          detail = esc(s.major) + " · lulus " + s.grad + "<br>profil " + completeness(s) + "% lengkap";
        }
        var nama = u.role === "company" ? company(u.companyId).name : u.name;
        return '<tr><td><div class="cell-main">' + esc(nama) + '</div><div class="cell-sub">' + esc(u.email) + '</div></td>' +
          '<td><span class="badge ' + CLS[u.role] + '">' + LBL[u.role] + '</span></td>' +
          '<td class="cell-sub">' + detail + '</td>' +
          '<td class="nowrap cell-sub">' + tgl(u.joined) + '</td>' +
          '<td><span class="badge ' + (u.active ? "ok" : "muted") + '">' + (u.active ? "Aktif" : "Nonaktif") + '</span></td>' +
          '<td class="right"><button class="btn btn-outline btn-sm" data-action="toggle-user" data-id="' + u.id + '">' +
          (u.active ? "Nonaktifkan" : "Aktifkan") + '</button></td></tr>';
      }).join("") + '</tbody></table></div></div>';
  }

  function pageAdminLaporan() {
    var perJurusan = {};
    DB.seekers.forEach(function (s) {
      perJurusan[s.major] = perJurusan[s.major] || { pelamar: 0, lamaran: 0, diterima: 0 };
      perJurusan[s.major].pelamar++;
    });
    DB.applications.forEach(function (a) {
      var s = seeker(a.seekerId);
      if (!s || !perJurusan[s.major]) return;
      perJurusan[s.major].lamaran++;
      if (a.status === "accepted") perJurusan[s.major].diterima++;
    });

    var perPerusahaan = DB.companies.map(function (c) {
      var jobs = DB.jobs.filter(function (j) { return j.companyId === c.id; });
      var lam = jobs.reduce(function (m, j) { return m + appsOfJob(j.id).length; }, 0);
      return { nama: c.name, lowongan: jobs.length, lamaran: lam };
    }).sort(function (a, b) { return b.lamaran - a.lamaran; });

    var perBulan = {};
    DB.applications.forEach(function (a) {
      var m = Number(String(a.created).slice(5, 7));
      perBulan[m] = (perBulan[m] || 0) + 1;
    });
    var maxB = Math.max.apply(null, Object.keys(perBulan).map(function (k) { return perBulan[k]; }).concat([1]));
    var namaBulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"];

    return '<div class="page-head"><div><h1>Laporan &amp; Rekap Penyaluran</h1>' +
      '<p>Bahan pelaporan BKK ke sekolah dan dinas terkait.</p></div>' +
      '<div class="btn-group"><button class="btn btn-outline" data-action="ekspor" data-jenis="lamaran">' + ICON('download') + ' Lamaran</button>' +
      '<button class="btn btn-outline" data-action="ekspor" data-jenis="lowongan">' + ICON('download') + ' Lowongan</button>' +
      '<button class="btn btn-primary" data-action="cetak">' + ICON('printer') + ' Cetak</button></div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Lamaran per bulan — tahun 2026</h2></div>' +
      '<div class="card-body"><div class="bars">' +
      namaBulan.map(function (nm, i) {
        var n = perBulan[i + 1] || 0;
        return '<div class="bar"><b>' + n + '</b><i style="height:' + (n / maxB * 100).toFixed(1) + '%"></i>' +
          '<small>' + nm + '</small></div>';
      }).join("") + '</div></div></div>' +
      '<div class="grid grid-2">' +
      '<div class="card"><div class="card-head"><h2>Rekap per kompetensi keahlian</h2></div>' +
      '<div class="table-wrap"><table class="data"><thead><tr><th>Kompetensi Keahlian</th>' +
      '<th class="right">Pelamar</th><th class="right">Lamaran</th><th class="right">Diterima</th><th class="right">%</th>' +
      '</tr></thead><tbody>' + Object.keys(perJurusan).map(function (k) {
        var r = perJurusan[k], pct = r.lamaran ? (r.diterima / r.lamaran * 100) : 0;
        return '<tr><td class="cell-main">' + esc(k) + '</td><td class="right">' + r.pelamar + '</td>' +
          '<td class="right">' + r.lamaran + '</td><td class="right">' + r.diterima + '</td>' +
          '<td class="right"><span class="badge ' + (pct > 20 ? "ok" : "muted") + '">' + pct.toFixed(1) + '%</span></td></tr>';
      }).join("") + '</tbody></table></div></div>' +
      '<div class="card"><div class="card-head"><h2>Perusahaan paling aktif</h2></div>' +
      '<div class="table-wrap"><table class="data"><thead><tr><th>Perusahaan</th>' +
      '<th class="right">Lowongan</th><th class="right">Lamaran masuk</th></tr></thead><tbody>' +
      perPerusahaan.map(function (r) {
        return '<tr><td class="cell-main">' + esc(r.nama) + '</td><td class="right">' + r.lowongan + '</td>' +
          '<td class="right">' + r.lamaran + '</td></tr>';
      }).join("") + '</tbody></table></div></div></div>';
  }

  function pageAdminPengumuman() {
    return '<div class="page-head"><div><h1>Pengumuman BKK</h1><p>Tampil pada beranda portal publik.</p></div></div>' +
      '<div class="card mb-3"><div class="card-head"><h2>Buat pengumuman baru</h2></div><div class="card-body">' +
      '<form data-form="pengumuman"><div class="field"><label>Judul <span class="req">*</span></label>' +
      '<input type="text" name="title" required></div>' +
      '<div class="field"><label>Isi pengumuman <span class="req">*</span></label>' +
      '<textarea name="body" required maxlength="2000" style="min-height:120px"></textarea></div>' +
      '<label class="check mb-2"><input type="checkbox" name="published" checked>' +
      '<span>Tampilkan di beranda portal.</span></label>' +
      '<button class="btn btn-primary" type="submit">' + ICON('megaphone') + ' Terbitkan</button></form></div></div>' +
      '<div class="card"><div class="card-head"><h2>Daftar pengumuman (' + DB.announcements.length + ')</h2></div>' +
      '<div class="card-body">' + (DB.announcements.length ? DB.announcements.map(function (a) {
        return '<div style="padding:.85rem 0;border-bottom:1px solid var(--line)">' +
          '<div class="flex between items-center gap wrap"><div style="min-width:0;flex:1">' +
          '<h3 style="margin-bottom:.15rem">' + esc(a.title) + ' <span class="badge ' + (a.published ? "ok" : "muted") + '">' +
          (a.published ? "Tayang" : "Arsip") + '</span></h3>' +
          '<div class="cell-sub">' + tgl(a.created) + '</div>' +
          '<p class="small muted mt-1 mb-0">' + esc(a.body) + '</p></div>' +
          '<div class="btn-group"><button class="btn btn-outline btn-sm" data-action="toggle-pengumuman" data-id="' + a.id + '">' +
          (a.published ? "Arsipkan" : "Tayangkan") + '</button>' +
          '<button class="btn btn-ghost btn-sm" data-action="hapus-pengumuman" data-id="' + a.id + '">Hapus</button>' +
          '</div></div></div>';
      }).join("") : empty("megaphone", "Belum ada pengumuman", "Buat pengumuman pertama pada formulir di atas.")) + '</div></div>';
  }

  function pageAdminLog() {
    return '<div class="page-head"><div><h1>Log Aktivitas</h1>' +
      '<p>' + DB.logs.length + ' kejadian tercatat untuk keperluan audit.</p></div></div>' +
      '<div class="card"><div class="table-wrap"><table class="data"><thead><tr>' +
      '<th>Waktu</th><th>Pelaku</th><th>Aksi</th><th>Keterangan</th></tr></thead><tbody>' +
      DB.logs.map(function (l) {
        return '<tr><td class="nowrap cell-sub">' + tglJam(l.at) + '</td><td class="cell-main">' + esc(l.actor) + '</td>' +
          '<td><span class="badge muted">' + esc(l.action) + '</span></td>' +
          '<td class="cell-sub">' + esc(l.detail) + '</td></tr>';
      }).join("") + '</tbody></table></div></div>';
  }

  // ── Kerangka halaman ────────────────────────────────────────────────────
  function navbar() {
    var u = user();
    var path = location.hash.split("?")[0];
    function link(href, label) {
      return '<a href="' + href + '" class="' + (path === href ? "active" : "") + '">' + label + '</a>';
    }
    var akun;
    if (u) {
      var home = u.role === "admin" ? "#/admin" : u.role === "company" ? "#/perusahaan" : "#/pelamar";
      var nama = u.role === "company" ? company(u.companyId).name : u.name;
      akun = '<a href="' + home + '" class="btn btn-outline btn-sm">' +
        ICON(u.role === "admin" ? "shield" : u.role === "company" ? "building" : "target") + ' Dashboard</a>' +
        '<span class="avatar" title="' + esc(nama) + '">' + esc(inisial(nama)) + '</span>' +
        '<button class="btn btn-ghost btn-sm" data-action="logout">Keluar</button>';
    } else {
      akun = '<a href="#/masuk" class="btn btn-primary btn-sm">Masuk / Pilih Peran</a>';
    }

    return '<div class="topbar"><div class="container">' +
      '<span>' + ICON('pin') + ' ' + SEKOLAH + ' — Jl. AKBP. R. Agil Kusumadya No.1, Pati, Jawa Tengah</span>' +
      '<span>' + ICON('mail') + ' bkk@smkn1pati.sch.id · ' + ICON('phone') + ' (0295) 381768</span></div></div>' +
      '<header class="navbar"><div class="container">' +
      '<a href="#/" class="brand"><span class="brand-mark">BKK</span>' +
      '<span class="brand-text"><b>Bursa Kerja Khusus</b><span>' + SEKOLAH + '</span></span></a>' +
      '<button class="nav-toggle" type="button" aria-label="Buka menu"><span></span><span></span><span></span></button>' +
      '<nav class="nav-links">' + link("#/", "Beranda") + link("#/lowongan", "Lowongan") +
      link("#/mitra", "Perusahaan Mitra") + link("#/tentang", "Tentang BKK") +
      '<div class="nav-actions">' + akun + '</div></nav></div></header>';
  }

  function demoBar() {
    var u = user();
    return '<div class="demo-bar"><div class="container">' +
      '<span>' + ICON('info') + ' <b>Mode Demo GitHub Pages</b> — data disimpan di peramban Anda, bukan di server. ' +
      'Versi produksi berjalan di FastAPI + PostgreSQL.</span>' +
      '<span class="role-switch">' +
      [[1, "Admin"], [2, "Perusahaan"], [10, "Pencari Kerja"]].map(function (r) {
        return '<button data-action="login" data-id="' + r[0] + '" class="' +
          (u && u.id === r[0] ? "active" : "") + '">' + r[1] + '</button>';
      }).join("") +
      '<button data-action="reset">' + ICON('history', 'xs') + ' Reset data</button></span></div></div>';
  }

  function footer() {
    return '<footer class="site"><div class="container"><div class="cols">' +
      '<div><a href="#/" class="brand" style="color:#fff"><span class="brand-mark">BKK</span>' +
      '<span class="brand-text"><b style="color:#fff">Bursa Kerja Khusus</b>' +
      '<span style="color:#a9c0da">' + SEKOLAH + '</span></span></a>' +
      '<p class="mt-2" style="max-width:34ch">Menjembatani lulusan ' + SEKOLAH + ' dengan dunia usaha dan dunia industri ' +
      'melalui informasi lowongan yang terverifikasi.</p></div>' +
      '<div><h4>Portal</h4><a href="#/lowongan">Cari Lowongan</a><a href="#/mitra">Perusahaan Mitra</a>' +
      '<a href="#/masuk">Masuk / Pilih Peran</a></div>' +
      '<div><h4>Informasi</h4><a href="#/tentang">Tentang BKK</a><a href="#/admin">Panel Admin</a>' +
      '<a href="#/perusahaan">Dashboard Perusahaan</a><a href="#/pelamar">Dashboard Pelamar</a></div>' +
      '<div><h4>Kontak</h4><p style="color:#a9c0da">Jl. AKBP. R. Agil Kusumadya No.1, Pati</p>' +
      '<a href="tel:0295381768">(0295) 381768</a><a href="mailto:bkk@smkn1pati.sch.id">bkk@smkn1pati.sch.id</a></div>' +
      '</div><div class="copyright"><span>© BKK ' + SEKOLAH + ' — Pratinjau demo statis.</span>' +
      '<span>Demo GitHub Pages · sinkron dengan aplikasi FastAPI</span></div></div></footer>';
  }

  // ── Router ──────────────────────────────────────────────────────────────
  function guard(role) {
    var u = user();
    if (!u) { flash("Silakan pilih peran terlebih dahulu untuk membuka dashboard.", "warning"); go("#/masuk"); return false; }
    if (u.role !== role) {
      flash("Akun " + u.role + " tidak memiliki akses ke halaman tersebut. Gunakan pengalih peran di atas.", "danger");
      go("#/masuk"); return false;
    }
    return true;
  }

  function route() {
    var raw = location.hash.replace(/^#\/?/, "");
    var parts = raw.split("?");
    var path = parts[0].split("/").filter(Boolean);
    var qs = new URLSearchParams(parts[1] || "");

    if (!path.length) return { full: true, html: pageBeranda() };

    switch (path[0]) {
      case "lowongan":
        return path[1] ? { html: pageLowonganDetail(path[1]) } : { html: pageLowongan(qs) };
      case "mitra":
        return path[1] ? { html: pageMitraDetail(path[1]) } : { html: pageMitra(qs) };
      case "tentang": return { html: pageTentang() };
      case "masuk": return { html: pageMasuk() };
      case "pelamar":
        if (!guard("seeker")) return { html: "" };
        if (path[1] === "lamaran") return { dash: "seeker", path: path, html: pageSeekerLamaran(qs) };
        if (path[1] === "tersimpan") return { dash: "seeker", path: path, html: pageSeekerTersimpan() };
        if (path[1] === "profil") return { dash: "seeker", path: path, html: pageSeekerProfil() };
        return { dash: "seeker", path: path, html: pageSeekerDashboard() };
      case "perusahaan":
        if (!guard("company")) return { html: "" };
        if (path[1] === "lowongan") {
          if (path[2] === "baru") return { dash: "company", path: path, html: pageCompanyJobForm(null) };
          if (path[2]) return { dash: "company", path: path, html: pageCompanyJobForm(path[2]) };
          return { dash: "company", path: path, html: pageCompanyJobs(qs) };
        }
        if (path[1] === "pelamar") {
          return path[2]
            ? { dash: "company", path: path, html: pageCompanyPelamarDetail(path[2]) }
            : { dash: "company", path: path, html: pageCompanyPelamar(qs) };
        }
        if (path[1] === "profil") return { dash: "company", path: path, html: pageCompanyProfil() };
        return { dash: "company", path: path, html: pageCompanyDashboard() };
      case "admin":
        if (!guard("admin")) return { html: "" };
        if (path[1] === "perusahaan") return { dash: "admin", path: path, html: pageAdminPerusahaan(qs) };
        if (path[1] === "lowongan") return { dash: "admin", path: path, html: pageAdminLowongan(qs) };
        if (path[1] === "lamaran") return { dash: "admin", path: path, html: pageAdminLamaran(qs) };
        if (path[1] === "pengguna") return { dash: "admin", path: path, html: pageAdminPengguna(qs) };
        if (path[1] === "laporan") return { dash: "admin", path: path, html: pageAdminLaporan() };
        if (path[1] === "pengumuman") return { dash: "admin", path: path, html: pageAdminPengumuman() };
        if (path[1] === "log") return { dash: "admin", path: path, html: pageAdminLog() };
        return { dash: "admin", path: path, html: pageAdminDashboard() };
      default:
        return { html: pageError(404, "Halaman tidak ditemukan.") };
    }
  }

  function render() {
    var r = route();
    var isi = r.dash ? dashboardShell(r.dash, r.path, r.html) : r.html;
    var flashes = takeFlash();
    var alerts = flashes.length ? '<div class="flash-wrap"><div class="container mt-2">' +
      flashes.map(function (f) {
        var ico = { success: "verified", danger: "alert", warning: "warning", info: "info" }[f.category] || "info";
        return '<div class="alert alert-' + f.category + '"><span>' + ICON(ico, "md") + '</span><span>' + esc(f.message) + '</span></div>';
      }).join("") + '</div></div>' : "";

    document.getElementById("app").innerHTML =
      demoBar() + navbar() + alerts +
      (r.full ? isi : '<main><div class="container">' + isi + '</div></main>') + footer();

    var t = document.querySelector(".nav-toggle"), l = document.querySelector(".nav-links");
    if (t && l) t.addEventListener("click", function () { l.classList.toggle("open"); });
    window.scrollTo(0, 0);
  }

  // ── Aksi ────────────────────────────────────────────────────────────────
  function csv(jenis) {
    var rows;
    if (jenis === "lowongan") {
      rows = [["ID", "Judul", "Perusahaan", "Lokasi", "Jurusan", "Status", "Kuota", "Deadline"]].concat(
        DB.jobs.map(function (j) {
          return [j.id, j.title, company(j.companyId).name, j.location, j.major || "-",
                  j.status, j.quota, j.deadline || "-"];
        }));
    } else if (jenis === "perusahaan") {
      rows = [["ID", "Nama", "Bidang", "Kota", "Status", "Kontak", "Telepon", "Terdaftar"]].concat(
        DB.companies.map(function (c) {
          return [c.id, c.name, c.industry, c.city, c.status, c.pic, c.phone, c.joined];
        }));
    } else {
      rows = [["ID", "Pelamar", "NIS", "Jurusan", "Lulus", "Lowongan", "Perusahaan", "Status", "Tanggal"]].concat(
        DB.applications.map(function (a) {
          var s = seeker(a.seekerId), su = seekerUser(s.id), j = job(a.jobId);
          return [a.id, su.name, s.nis, s.major, s.grad, j.title, company(j.companyId).name, a.status, a.created];
        }));
    }
    var teks = rows.map(function (r) {
      return r.map(function (v) { return '"' + String(v).replace(/"/g, '""') + '"'; }).join(",");
    }).join("\n");
    var blob = new Blob(["﻿" + teks], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = "bkk-" + jenis + "-2026.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    flash("Berkas CSV " + jenis + " diunduh.", "success");
    render();
  }

  function addLog(action, detail) {
    var u = user();
    DB.logs.unshift({
      at: new Date().toISOString().slice(0, 16).replace("T", " "),
      actor: u ? (u.role === "company" ? company(u.companyId).name : u.name) : "Anonim",
      action: action, detail: detail
    });
  }

  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-action]");
    if (!el) return;
    var act = el.getAttribute("data-action");
    var id = Number(el.getAttribute("data-id"));

    if (act === "login") {
      setSession(id);
      var u = user();
      flash("Masuk sebagai " + (u.role === "company" ? company(u.companyId).name : u.name) + ".", "success");
      go(u.role === "admin" ? "#/admin" : u.role === "company" ? "#/perusahaan" : "#/pelamar");
      return;
    }
    if (act === "logout") { setSession(null); flash("Anda telah keluar.", "info"); go("#/"); return; }
    if (act === "reset") {
      if (confirm("Kembalikan seluruh data demo ke kondisi awal?")) resetDemo();
      return;
    }
    if (act === "ekspor") { csv(el.getAttribute("data-jenis")); return; }
    if (act === "cetak") { window.print(); return; }

    if (act === "toggle-simpan") {
      var s = mySeeker();
      if (!s) { flash("Masuk sebagai pencari kerja untuk menyimpan lowongan.", "warning"); go("#/masuk"); return; }
      var i = DB.saved.findIndex(function (x) { return x.jobId === id && x.seekerId === s.id; });
      if (i >= 0) { DB.saved.splice(i, 1); flash("Lowongan dihapus dari daftar tersimpan.", "info"); }
      else { DB.saved.push({ jobId: id, seekerId: s.id }); flash("Lowongan disimpan.", "success"); }
      save(); render(); return;
    }
    if (act === "batal-lamaran") {
      if (!confirm("Batalkan lamaran ini?")) return;
      var a = DB.applications.find(function (x) { return x.id === id; });
      a.status = "withdrawn"; a.updated = "2026-08-26";
      addLog("withdraw", "Membatalkan lamaran #" + a.id);
      save(); flash("Lamaran dibatalkan.", "info"); render(); return;
    }
    if (act === "tutup-lowongan") {
      var j = job(id); j.status = "closed";
      addLog("close_job", "Menutup lowongan '" + j.title + "'");
      save(); flash("Lowongan ditutup.", "info"); render(); return;
    }
    if (act === "hapus-lowongan") {
      if (!confirm("Hapus lowongan ini secara permanen?")) return;
      var jj = job(id);
      DB.jobs = DB.jobs.filter(function (x) { return x.id !== id; });
      addLog("delete_job", "Menghapus lowongan '" + jj.title + "'");
      save(); flash("Lowongan dihapus.", "info"); render(); return;
    }
    if (act === "verif-perusahaan") {
      var c = company(id); c.status = el.getAttribute("data-status"); c.note = null;
      addLog("verify_company", c.name + " ' + ICON('arrow-right', 'xs') + ' " + c.status);
      save(); flash("Status " + c.name + " diperbarui.", "success"); render(); return;
    }
    if (act === "moderasi-lowongan") {
      var mj = job(id); mj.status = el.getAttribute("data-status");
      if (mj.status === "published" && !mj.published) mj.published = "2026-08-26";
      addLog("moderate_job", "'" + mj.title + "' ' + ICON('arrow-right', 'xs') + ' " + mj.status);
      save(); flash("Lowongan '" + mj.title + "' diperbarui.", "success"); render(); return;
    }
    if (act === "toggle-user") {
      var tu = DB.users.find(function (x) { return x.id === id; });
      if (session && tu.id === session.userId) { flash("Anda tidak dapat menonaktifkan akun sendiri.", "warning"); render(); return; }
      tu.active = !tu.active;
      addLog("toggle_user", tu.email + " ' + ICON('arrow-right', 'xs') + ' " + (tu.active ? "aktif" : "nonaktif"));
      save(); flash("Akun " + tu.email + " kini " + (tu.active ? "aktif" : "nonaktif") + ".", "success"); render(); return;
    }
    if (act === "toggle-pengumuman") {
      var an = DB.announcements.find(function (x) { return x.id === id; });
      an.published = !an.published; save();
      flash("Pengumuman diperbarui.", "success"); render(); return;
    }
    if (act === "hapus-pengumuman") {
      if (!confirm("Hapus pengumuman ini?")) return;
      DB.announcements = DB.announcements.filter(function (x) { return x.id !== id; });
      save(); flash("Pengumuman dihapus.", "info"); render(); return;
    }
  });

  document.addEventListener("submit", function (e) {
    var form = e.target.closest("[data-form]");
    if (!form) return;
    e.preventDefault();
    var kind = form.getAttribute("data-form");
    var id = Number(form.getAttribute("data-id"));
    var d = new FormData(form);
    function val(k) { return (d.get(k) || "").toString().trim(); }

    if (kind === "cari-beranda" || kind === "filter-lowongan") {
      var p = new URLSearchParams();
      ["q", "lokasi", "jurusan", "tipe", "urut"].forEach(function (k) { if (val(k)) p.set(k, val(k)); });
      go("#/lowongan" + (p.toString() ? "?" + p : "")); return;
    }
    if (kind === "cari-mitra") {
      go("#/mitra" + (val("q") ? "?q=" + encodeURIComponent(val("q")) : "")); return;
    }
    if (kind === "filter-pelamar") {
      var pp = new URLSearchParams();
      ["job", "status", "q"].forEach(function (k) { if (val(k)) pp.set(k, val(k)); });
      go("#/perusahaan/pelamar" + (pp.toString() ? "?" + pp : "")); return;
    }

    if (kind === "lamar") {
      var s = mySeeker();
      DB.applications.push({
        id: nextId(DB.applications), jobId: id, seekerId: s.id, status: "submitted",
        created: "2026-08-26", updated: "2026-08-26", cover: val("cover") || null
      });
      if (!s.cv) s.cv = true;
      addLog("apply", "Melamar '" + job(id).title + "' di " + company(job(id).companyId).name);
      save(); flash("Lamaran berhasil dikirim. Pantau statusnya di menu Lamaran Saya.", "success");
      go("#/pelamar/lamaran"); return;
    }

    if (kind === "profil-pelamar") {
      var ps = mySeeker(), pu = user();
      pu.name = val("name") || pu.name;
      ["nis", "phone", "gender", "birth", "city", "major", "headline", "summary", "skills", "education", "experience"]
        .forEach(function (k) { ps[k] = val(k) || null; });
      ps.grad = Number(val("grad")) || null;
      ps.openToWork = !!d.get("openToWork");
      if (d.get("cv") && d.get("cv").name) ps.cv = true;
      if (d.get("photo") && d.get("photo").name) ps.photo = true;
      addLog("update_profile", "Profil pencari kerja diperbarui");
      save(); flash("Profil berhasil disimpan.", "success"); render(); return;
    }

    if (kind === "simpan-lowongan") {
      var aksi = (e.submitter && e.submitter.value) || "submit";
      var c = myCompany();
      var j = id ? job(id) : null;
      if (!j) {
        j = { id: nextId(DB.jobs), companyId: c.id, views: 0 };
        DB.jobs.push(j);
      }
      j.title = val("title");
      j.slug = (val("title") + "-" + c.name).toLowerCase()
        .normalize("NFD").replace(/[̀-ͯ]/g, "")
        .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + (id ? "" : "-" + j.id);
      j.desc = val("desc"); j.req = val("req") || null; j.benefit = val("benefit") || null;
      j.major = val("major") || null; j.type = val("type") || "full_time";
      j.location = val("location"); j.remote = !!d.get("remote");
      j.min = Number(val("min")) || null; j.max = Number(val("max")) || null;
      j.hidden = !!d.get("hidden");
      j.quota = Number(val("quota")) || 1;
      j.maxAge = Number(val("maxAge")) || null;
      j.deadline = val("deadline") || null;
      j.gender = "Semua";
      j.status = aksi === "draft" ? "draft" : "pending";
      addLog("save_job", c.name + " menyimpan lowongan '" + j.title + "' (" + j.status + ")");
      save();
      flash(aksi === "draft" ? "Lowongan disimpan sebagai draf."
        : "Lowongan dikirim dan menunggu persetujuan admin BKK.", "success");
      go("#/perusahaan/lowongan"); return;
    }

    if (kind === "status-pelamar") {
      var a = DB.applications.find(function (x) { return x.id === id; });
      a.status = val("status");
      a.note = val("note") || null;
      a.interview = val("interview") ? val("interview").replace("T", " ") : null;
      a.updated = "2026-08-26";
      addLog("update_application", "Status lamaran #" + a.id + " ' + ICON('arrow-right', 'xs') + ' " + a.status);
      save(); flash("Status pelamar diperbarui.", "success"); render(); return;
    }

    if (kind === "profil-perusahaan") {
      var pc = myCompany();
      ["name", "industry", "city", "employees", "address", "desc", "pic", "phone", "website"]
        .forEach(function (k) { if (val(k)) pc[k] = val(k); });
      addLog("update_company", "Profil " + pc.name + " diperbarui");
      save(); flash("Profil perusahaan berhasil disimpan.", "success"); render(); return;
    }

    if (kind === "verif-perusahaan") {
      var vc = company(id);
      vc.status = val("status"); vc.note = val("note") || null;
      addLog("verify_company", vc.name + " ' + ICON('arrow-right', 'xs') + ' " + vc.status);
      save(); flash("Status " + vc.name + " diperbarui menjadi " + DB.companyStatus[vc.status] + ".", "success");
      render(); return;
    }

    if (kind === "moderasi-lowongan") {
      var mj2 = job(id);
      mj2.status = val("status"); mj2.reviewNote = val("note") || null;
      if (mj2.status === "published" && !mj2.published) mj2.published = "2026-08-26";
      addLog("moderate_job", "'" + mj2.title + "' ' + ICON('arrow-right', 'xs') + ' " + mj2.status);
      save(); flash("Lowongan '" + mj2.title + "' diperbarui.", "success"); render(); return;
    }

    if (kind === "pengumuman") {
      DB.announcements.unshift({
        id: nextId(DB.announcements), title: val("title"), body: val("body"),
        published: !!d.get("published"), created: "2026-08-26"
      });
      addLog("announcement", val("title"));
      save(); flash("Pengumuman disimpan.", "success"); render(); return;
    }
  });

  window.addEventListener("hashchange", render);
  load();
  if (!location.hash) location.hash = "#/";
  render();
})();
