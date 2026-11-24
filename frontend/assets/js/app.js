/* IP 运营工作台 · 前端（免构建 Vue 3） */
(function () {
  "use strict";

  const { createApp } = Vue;

  const ICONS = {
    home:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 7.3 8 2.6l5.5 4.7v6.1a.8.8 0 0 1-.8.8H3.3a.8.8 0 0 1-.8-.8V7.3Z"/><path d="M6.3 14.2v-4h3.4v4"/></svg>',
    user:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="8" cy="5.4" r="2.5"/><path d="M3 13.2c.6-2.2 2.5-3.4 5-3.4s4.4 1.2 5 3.4"/></svg>',
    database:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><ellipse cx="8" cy="3.6" rx="5.2" ry="2.1"/><path d="M2.8 3.6v8.8c0 1.2 2.3 2.1 5.2 2.1s5.2-.9 5.2-2.1V3.6"/><path d="M2.8 8c0 1.2 2.3 2.1 5.2 2.1s5.2-.9 5.2-2.1"/></svg>',
    layers:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2.2 13.5 5 8 7.8 2.5 5 8 2.2Z"/><path d="m2.5 8 5.5 2.8L13.5 8"/><path d="m2.5 11 5.5 2.8L13.5 11"/></svg>',
    bulb:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M5.2 11.2c-1-.9-1.7-2.2-1.7-3.7a4.5 4.5 0 1 1 7.3 3.5c-.5.4-.8 1-.8 1.6H6c0-.6-.3-1.1-.8-1.4Z"/><path d="M6.3 14h3.4"/></svg>',
    pen:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11.6 2.7 13.3 4.4 5.6 12.1l-2.4.7.7-2.4 7.7-7.7Z"/><path d="m9.9 4.4 1.7 1.7"/></svg>',
    calendar:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="2.5" y="3.5" width="11" height="10" rx="2"/><path d="M2.5 6.5h11M5.3 2.2v2.6M10.7 2.2v2.6"/></svg>',
    settings:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11"/><path d="M6 3v3M10 6.5v3M5 10v3"/></svg>',
    quill:
      '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12.7 2.2c-2.6.7-4.6 2.3-5.8 4.3-.8 1.4-1.1 2.8-1.1 4.2 1.4 0 2.8-.3 4.2-1.1 2-1.2 3.6-3.2 4.3-5.8"/><path d="M8.2 8.8 2.8 14"/><path d="M4.6 9.6h3"/></svg>',
  };

  const PAGES = {
    home: "首页",
    profile: "IP 档案",
    database: "数据库",
    deconstruct: "对标拆解",
    rewrite: "改写",
    topics: "选题库",
    writing: "写稿",
    plan: "内容计划",
    settings: "设置",
  };

  const SECTIONS = {
    home: "首页",
    profile: "IP 档案",
    database: "数据库",
    deconstruct: "对标拆解",
    rewrite: "改写",
    topics: "选题库",
    writing: "写稿",
    plan: "内容计划",
    settings: "设置",
  };

  const NAV_GROUPS = [
    { label: "工作台", items: [{ key: "home", label: "首页", icon: "home" }] },
    {
      label: "资产",
      items: [
        { key: "profile", label: "IP 档案", icon: "user" },
        { key: "database", label: "数据库", icon: "database" },
      ],
    },
    {
      label: "创作",
      items: [
        { key: "deconstruct", label: "对标拆解", icon: "layers" },
        { key: "rewrite", label: "改写", icon: "quill" },
        { key: "topics", label: "选题库", icon: "bulb" },
        { key: "writing", label: "写稿", icon: "pen" },
      ],
    },
    { label: "运营", items: [{ key: "plan", label: "内容计划", icon: "calendar" }] },
    { label: "系统", items: [{ key: "settings", label: "设置", icon: "settings" }] },
  ];

  const DEMO_METRICS = {
    followers: "3,210",
    newFollowers: "+46",
    totalViews: "12,480",
    topViews: "4,206",
    topTitle: "《一条视频让你学懂“钙”》",
    engagement: "4.2%",
    engagementDelta: "-0.3%",
    syncedAt: "11-12 09:30",
  };

  const DEMO_FOCUS = [
    {
      title: "拆解 1 条母婴对标",
      meta: "《一条视频让你学懂“钙”》· 30 分钟",
      tag: "进行中",
      tagClass: "green",
      action: "继续",
      route: "deconstruct",
    },
    {
      title: "写稿：春季补钙选题",
      meta: "标题 + 口播稿 + 分镜 · 45 分钟",
      tag: "待开始",
      tagClass: "gold",
      action: "开始",
      route: "writing",
    },
    {
      title: "确认本周排期",
      meta: "本周 3 条内容，已排 1 条 · 15 分钟",
      tag: "今天截止",
      tagClass: "peach",
      action: "去排期",
      route: "plan",
    },
  ];

  const DEMO_TOPICS = [
    {
      title: "为什么你补的钙，孩子根本没吸收",
      meta: "角度：把“补钙”拆成吸收率 · 来源：拆解《一条视频让你学懂“钙”》",
      tag: "拆解",
      tagClass: "green",
    },
    {
      title: "春季长高，家长最该盯的不是钙",
      meta: "角度：睡眠和运动的优先级 · 来源：每日抓取 · 热榜",
      tag: "抓取",
      tagClass: "gold",
    },
    {
      title: "母婴店不会告诉你的 3 个补钙误区",
      meta: "角度：站在家长这边说真话 · 来源：手动添加",
      tag: "手动",
      tagClass: "peach",
    },
  ];

  const DEMO_WEEK = [
    { day: "周一", text: "拆 2 条对标 · 已完成 1 条", dot: "on" },
    { day: "周二", text: "写稿 · 春季补钙选题", dot: "hot" },
    { day: "周三", text: "拍摄 + 粗剪", dot: "" },
    { day: "周四", text: "发布第 2 条", dot: "" },
    { day: "周五", text: "T+1 数据复盘", dot: "" },
  ];

  const PLACEHOLDERS = {
    profile: {
      title: "IP 档案还没开始",
      desc: "定位、受众、内容支柱和表达风格。所有创作都从这里取上下文，改一次，后续的稿子都会跟着变。",
      note: "这一页会在写稿台之前接入。",
      icon: "◉",
    },
    topics: {
      title: "选题库还没开始",
      desc: "选题有两个来源：从对标拆解里长出来的，以及每天主动抓取、和 IP 相关的。",
      note: "第一版先把对标拆解跑通，抓取选题后面接。",
      icon: "✦",
    },
    writing: {
      title: "写稿台还没开始",
      desc: "标题、口播稿和分镜会写在同一张场记单上，改稿保留版本，不覆盖上一版。",
      note: "写稿的输入是拆解结果。先拆一条，再谈写。",
      icon: "✎",
    },
    plan: {
      title: "内容计划还没开始",
      desc: "把选题放进日历，按你的产能排出节奏。计划不是待办清单，而是这周要交付什么的承诺。",
      note: "这一页会在选题库可用之后接入。",
      icon: "▦",
    },
  };

  function api(path, options) {
    return fetch("/api" + path, options).then(async (res) => {
      if (!res.ok) {
        let message = "请求失败";
        try {
          const body = await res.json();
          message = body.detail || message;
        } catch (e) {}
        throw new Error(message);
      }
      return res.json();
    });
  }

  const app = createApp({
    data() {
      return {
        icons: ICONS,
        navGroups: NAV_GROUPS,
        route: "home",
        overview: null,
        items: [],
        current: null,
        settings: null,
        query: "",
        listFilter: "all",
        decoTab: "video",
        viewer: null,
        noteTab: "desc",
        accountForm: { name: "", platform: "视频号", links: "", storyboard: true },
        accountSubmitting: false,
        accountProgress: "",
        accounts: [],
        accountCurrent: null,
        accountNickname: "",
        accountPages: 2,
        accountMode: "m3",
        collectRange: "m3",
        previewData: null,
        rangeOptions: [
          { key: "m1", label: "近 1 个月" },
          { key: "m3", label: "近 3 个月" },
          { key: "m6", label: "近 6 个月" },
          { key: "y1", label: "近 1 年" },
          { key: "all", label: "全部历史" },
        ],
        accountBusy: false,
        accountMessage: "",
        accountMessageBad: false,
        phoneLinks: [],
        linkPrompt: { open: false, video: null, text: "", busy: false },
        filterDays: 30,
        filterMetric: "shares",
        filterMin: 100,
        onlyQualified: false,
        videoView: "boards",
        spendToday: null,
        videoBusyId: "",
        tab: "script",
        dbTab: "review",
        modalOpen: false,
        submitting: false,
        dragging: false,
        file: null,
        form: { title: "", author: "", platform: "视频号", url: "", storyboard: true },
        toastMsg: "",
        toastTimer: null,
        syncing: false,
        scanning: false,
        loginScan: {},
        asrModel: "medium",
        llmForm: { base_url: "", model: "", api_key: "" },
        llmTest: "",
        llmMessage: "",
        llmMessageBad: false,
        savingLlm: false,
        testingLlm: false,
        tikhubForm: { api_key: "" },
        tikhubId: "sphQCIRCN4HiGA",
        dataxForm: { api_key: "" },
        dataxNickname: "玖妈懂敏宝",
        dataxMsg: "",
        dataxMsgBad: false,
        savingDatax: false,
        testingDatax: false,
        tikhubMsg: "",
        tikhubMsgBad: false,
        savingTikhub: false,
        testingTikhub: false,
        ocrForm: { base_url: "", model: "", api_key: "" },
        ocrTest: "",
        ocrMessage: "",
        ocrMessageBad: false,
        savingOcr: false,
        testingOcr: false,
        linkScanning: false,
        subView: "segments",
        rewriteView: "parts",
        rewriteLoading: false,
        rewriteError: "",
        metricsList: [],
        paletteOpen: false,
        paletteQuery: "",
        paletteIndex: 0,
        pollTimer: null,
        now: new Date(),
      };
    },
    computed: {
      // 图文笔记：没有字幕、分镜和时间轴，走另一套展示
      isNote() {
        return !!(this.current && this.current.data && this.current.data.kind === "image_note");
      },
      noteImages() {
        if (!this.isNote) return [];
        const sid = this.current.source_id || "";
        const list = this.current.data.images || [];
        return list.map((img, i) => {
          // 角色按位置定：第 1 张封面，最后一张结束，中间依次内页1、内页2……
          const role = i === 0 ? "封面" : (i === list.length - 1 ? "结束" : `内页${i}`);
          let title = img.title || "";
          let paragraphs = (img.paragraphs || []).filter((p) => p && p.trim());
          // 老数据没分过标题/正文，退回按行拆，避免空白
          if (!title && !paragraphs.length && img.text) {
            const lines = String(img.text).split("\n").filter((x) => x.trim());
            title = lines[0] || "";
            paragraphs = lines.slice(1);
          }
          return {
            ...img,
            role,
            title,
            paragraphs,
            url: img.file && sid ? `/media/notes/${sid}/${img.file}` : "",
          };
        });
      },
      noteKeywords() {
        const ta = this.current && this.current.data && this.current.data.title_analysis;
        return (ta && ta.keywords) || [];
      },
      noteTags() {
        const d = this.current && this.current.data;
        if (!d) return [];
        if (d.tags && d.tags.length) return d.tags;
        // 老记录里没有 tags 字段时，从正文里现抠，避免为此重跑一次云端拆解
        const out = [];
        const re = /#([^#\s]{1,30}?)(?:\[话题\])?#/g;
        let m;
        while ((m = re.exec(d.desc || ""))) {
          const t = (m[1] || "").trim();
          if (t && !out.includes(t)) out.push(t);
        }
        return out;
      },
      noteDescClean() {
        const d = (this.current && this.current.data && this.current.data.desc) || "";
        // 正文里混着的 #话题# 标签去掉，标签在上面单独展示
        return d.replace(/#[^#\s]{1,30}(?:\[话题\])?#/g, "")
          .replace(/[ \t]{2,}/g, " ")
          .replace(/\n{3,}/g, "\n\n")
          .trim();
      },
      noteDescText() {
        if (!this.isNote) return "";
        const title = this.current.title || (this.current.data && this.current.data.title) || "";
        return `标题：${title}\n\n${this.noteDescClean}`;
      },
      noteImagesText() {
        if (!this.isNote) return "";
        return this.noteImages.map((img) => {
          const parts = [`【${img.role}】`];
          if (img.title) parts.push(img.title);
          if (img.paragraphs.length) parts.push(img.paragraphs.join("\n"));
          return parts.join("\n");
        }).join("\n\n");
      },
      noteAllText() {
        return [this.noteDescText, this.noteImagesText].filter(Boolean).join("\n\n");
      },
      pageTitle() { return PAGES[this.route] || "首页"; },
      sectionLabel() { return SECTIONS[this.route] || "首页"; },
      isDemo() { return !this.settings || this.settings.demo_mode !== false; },
      todayLabel() {
        const d = this.now;
        const w = "日一二三四五六"[d.getDay()];
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} 周${w}`;
      },
      greeting() {
        const h = this.now.getHours();
        if (h < 6) return "凌晨好";
        if (h < 11) return "早上好";
        if (h < 14) return "中午好";
        if (h < 18) return "下午好";
        return "晚上好";
      },
      metrics() {
        const m = this.overview && this.overview.metrics;
        if (m) {
          const num = (v) => Number(v || 0).toLocaleString("zh-CN");
          const net = Number(m.followersNet || 0);
          return {
            followers: num(m.followers),
            net,
            newFollowers: net > 0 ? `↑ ${num(net)} 净增` : net < 0 ? `↓ ${num(-net)} 净减` : "持平",
            totalViews: num(m.totalViews),
            topViews: num(m.topViews),
            topTitle: m.topTitle || "",
            engagement: Number(m.engagement || 0).toFixed(2) + "%",
            syncedAt: (m.date || "") + " 数据",
            date: m.date || "",
            real: true,
          };
        }
        if (!this.isDemo) {
          return {
            followers: "—", net: 0, newFollowers: "待同步", totalViews: "—",
            topViews: "—", topTitle: "", engagement: "—",
            engagementDelta: "", syncedAt: "尚未同步", date: "", real: false,
          };
        }
        return Object.assign({ date: "", real: false }, DEMO_METRICS);
      },
      syncState() {
        return (this.overview && this.overview.sync) || {};
      },
      dataNote() {
        const s = this.syncState;
        if (s.running) return "正在同步…";
        if (s.status === "login_expired") return "登录已过期";
        if (s.status === "failed") return "同步失败";
        if (s.status === "ok" && s.date) return s.date;
        if (s.hasData) return "今日待同步";
        return "尚未同步";
      },
      needScan() {
        return this.syncState.status === "login_expired";
      },
      dataHint() {
        const s = this.syncState;
        if (this.scanning) return "正在等待扫码：请在刚弹出的 Chrome 窗口里用微信扫码，登录后窗口会自动关闭。";
        if (s.status === "login_expired") return "登录已过期：点「重新扫码」，用微信扫码后立刻会自动关闭浏览器，再点「同步数据」。";
        if (s.status === "failed") return "同步失败：" + (s.message || "未知原因");
        return "";
      },
      recentHeadline() {
        const m = this.overview && this.overview.metrics;
        if (m) {
          const net = m.followersNet;
          const netText = net === 0 ? "粉丝数持平" : `粉丝${net > 0 ? "净增 " + net : "净减 " + Math.abs(net)}`;
          return `昨日${netText}，总阅读 ${Number(m.totalViews || 0).toLocaleString("zh-CN")}，互动率 ${Number(m.engagement || 0).toFixed(2)}%。`;
        }
        const r = this.overview && this.overview.recent && this.overview.recent[0];
        if (!r) return "今天先拆一条，再写一条。";
        return `昨天发了 1 条，粉丝净增 46。最近一条是《${r.title}》。`;
      },
      sourceInfo() {
        return (this.current && this.current.source) || null;
      },
      subtitleState() {
        const s = this.sourceInfo;
        if (!s) return { kind: "none" };
        if (s.status === "transcribing") return { kind: "running", progress: s.progress };
        if (s.status === "transcribe_failed") return { kind: "failed", error: s.error || "转写失败" };
        if (s.transcript) return { kind: "done", demo: s.is_demo };
        if (s.has_file) return { kind: "ready" };
        return { kind: "no_file" };
      },
      subtitleSegments() {
        const s = this.sourceInfo;
        if (!s) return [];
        if (s.paragraphs && s.paragraphs.length) return s.paragraphs;
        return s.segments || [];
      },
      rewriteData() {
        const d = (this.current && this.current.data) || {};
        return d.rewrite || d.script || null;
      },
      fullScriptText() {
        const s = this.rewriteData || {};
        if (s.full_text) return s.full_text;
        return [s.opening, ...(s.body || []), s.ending].filter(Boolean).join("\n\n");
      },
      scriptSections() {
        const s = this.rewriteData || {};
        if (s.sections && s.sections.length) return s.sections;
        const out = [];
        if (s.opening) out.push({ role: "开头", text: s.opening });
        if (s.body && s.body.length) out.push({ role: "主体", text: (s.body || []).join("\n") });
        if (s.ending) out.push({ role: "结尾", text: s.ending });
        return out;
      },
      structureOutline() {
        const d = (this.current && this.current.data) || {};
        return d.structure || [];
      },
      rewriteItems() {
        return (this.items || []).filter((i) => i.status === "done");
      },
      subtitleMetaLine() {
        const s = this.sourceInfo;
        if (!s || !s.asr) return "";
        const bits = [];
        if (s.asr.model) bits.push(s.asr.model);
        if (s.asr.device) bits.push(s.asr.device === "cuda" ? "显卡" : "CPU");
        if (s.duration) bits.push(this.fmtSeconds(s.duration) + " 音频");
        if (s.asr.elapsed) bits.push("用时 " + s.asr.elapsed + " 秒");
        if (s.proofread) bits.push("已校对");
        if (s.ocr && s.ocr.clean) bits.push("已用画面字幕校正");
        return bits.join(" · ");
      },
      focusItems() {
        return DEMO_FOCUS;
      },
      topicItems() {
        return DEMO_TOPICS;
      },
      weekItems() {
        return DEMO_WEEK;
      },
      filteredItems() {
        // 账号来源的拆解也要显示，否则从账号页点「拆解这条」后回来就找不到了
        let list = this.items;
        if (this.listFilter === "done") list = list.filter((i) => i.status === "done");
        if (this.listFilter === "processing") {
          list = list.filter((i) => i.status === "processing" || i.status === "preparing");
        }
        const q = this.query.trim();
        if (q) list = list.filter((i) => (i.title || "").includes(q));
        return list;
      },
      processingCount() {
        return this.items.filter((i) => i.status === "processing" || i.status === "preparing").length;
      },
      doneCount() {
        return this.items.filter((i) => i.status === "done").length;
      },
      decomposedByVideo() {
        const map = {};
        const byTitle = {};
        for (const it of this.items) {
          const vid = it.options && it.options.video_id;
          if (vid && !map[vid]) map[vid] = it;
          const k = (it.title || "").slice(0, 12);
          if (k && !byTitle[k]) byTitle[k] = it;
        }
        // 老记录没有 video_id，按「标题前 12 字」兜底匹配，避免显示成未拆解又点一次
        const vids = (this.accountCurrent && this.accountCurrent.videos) || [];
        for (const v of vids) {
          if (map[v.id]) continue;
          const k = (v.text || "").slice(0, 12);
          if (k && byTitle[k]) map[v.id] = byTitle[k];
        }
        return map;
      },
      qualifiedVideos() {
        const videos = (this.accountCurrent && this.accountCurrent.videos) || [];
        const cutoff = Date.now() - Number(this.filterDays || 0) * 86400000;
        return videos.filter((v) => {
          const time = Date.parse(v.published_at || "");
          if (time && time < cutoff) return false;
          return this.qualifyValue(v) >= Number(this.filterMin || 0);
        });
      },
      accountVideosRanked() {
        const source = this.onlyQualified ? this.qualifiedVideos
          : (this.accountCurrent && this.accountCurrent.videos) || [];
        return [...source].sort((a, b) => this.engagement(b) - this.engagement(a));
      },
      accountMetrics() {
        return (this.accountCurrent && this.accountCurrent.metrics) || {};
      },
      linkedText() {
        const list = this.accountMetrics.linked || [];
        if (!list.length) return "无";
        return list.map((x) => x.nickname || x.type || "关联账号").join("、");
      },
      accountVerify() {
        const m = (this.accountCurrent && this.accountCurrent.metrics) || {};
        return m.verify || "";
      },
      accountRegion() {
        const m = (this.accountCurrent && this.accountCurrent.metrics) || {};
        return m.region || "";
      },
      accountBoards() {
        const all = (this.accountCurrent && this.accountCurrent.videos) || [];
        const byLikes = (a, b) => (b.likes || 0) - (a.likes || 0);
        const pinned = all.filter((v) => v.pinned);
        const rest = all.filter((v) => !v.pinned);
        const historical = [...rest].sort(byLikes).slice(0, 10);
        const cutoff = Date.now() - 90 * 86400000;
        const recentAll = rest.filter((v) => {
          const t = Date.parse(v.published_at || "");
          return t && t >= cutoff;
        });
        const recent = [...recentAll].sort(byLikes).slice(0, 10);
        return [
          { key: "pinned", title: "置顶作品", note: "账号自己置顶的，不限时间", items: pinned },
          { key: "history", title: "历史爆款榜 Top 10", note: "全部作品里点赞最高的 10 条", items: historical },
          { key: "recent", title: "近期榜 Top 10", note: `近 90 天共 ${recentAll.length} 条，取点赞最高 10 条`, items: recent },
        ].filter((b) => b.items.length || b.key === "pinned");
      },
      accountStats() {
        const list = this.accountVideosRanked;
        if (!list.length) return { count: 0, median: 0, top: 0, from: "", to: "" };
        const values = list.map((v) => this.engagement(v)).sort((a, b) => a - b);
        const median = values[Math.floor(values.length / 2)];
        const dates = list.map((v) => (v.published_at || "").slice(0, 10)).filter(Boolean).sort();
        return {
          count: list.length,
          median,
          top: values[values.length - 1],
          from: dates[0] || "",
          to: dates[dates.length - 1] || "",
        };
      },
      accountAnalysis() {
        const raw = this.accountCurrent && this.accountCurrent.analysis;
        if (!raw) return null;
        try { return JSON.parse(raw); } catch (e) { return null; }
      },
      accountGroups() {
        const groups = new Map();
        this.items.forEach((it) => {
          const name = (it.options && it.options.account) || "";
          if (!name) return;
          if (!groups.has(name)) {
            groups.set(name, { name, platform: it.platform || "—", items: [], done: 0 });
          }
          const g = groups.get(name);
          g.items.push(it);
          if (it.status === "done") g.done += 1;
        });
        return Array.from(groups.values()).map((g) => ({
          ...g,
          latest: g.items[0] ? g.items[0].created_at : "",
        }));
      },
      paletteCommands() {
        const cmds = [];
        this.navGroups.forEach((g) => {
          g.items.forEach((it) => {
            cmds.push({ label: it.label, icon: it.icon, k: g.label, run: () => this.go(it.key) });
          });
        });
        cmds.push({ label: "新建拆解", icon: "layers", k: "操作", run: () => this.openNew() });
        cmds.push({ label: "刷新数据", icon: "home", k: "操作", run: () => this.refresh() });
        return cmds;
      },
      paletteResults() {
        const q = this.paletteQuery.trim().toLowerCase();
        if (!q) return this.paletteCommands;
        return this.paletteCommands.filter((c) => c.label.toLowerCase().includes(q));
      },
      placeholder() {
        return PLACEHOLDERS[this.route] || PLACEHOLDERS.profile;
      },
      timeline() {
        const ret = (this.current && this.current.data && this.current.data.retention) || [];
        const segs = [];
        ret.forEach((r) => {
          const m = /(\d+):(\d+)\s*[–—\-~至]\s*(\d+):(\d+)/.exec(r.at || "");
          if (!m) return;
          const start = parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
          const end = parseInt(m[3], 10) * 60 + parseInt(m[4], 10);
          segs.push({ start, end, span: Math.max(1, end - start), label: r.at, move: r.move });
        });
        if (!segs.length) return [{ start: 0, end: 60, span: 60, label: "0:00–1:00", move: "" }];
        return segs;
      },
      retentionSummary() {
        const last = this.timeline[this.timeline.length - 1];
        return `${this.timeline.length} 个节点 / 共 ${this.fmtSeconds(last.end)}`;
      },
      scaleEnd() {
        const last = this.timeline[this.timeline.length - 1];
        return this.fmtSeconds(last.end);
      },
    },
    methods: {
      oneLine(text) {
        return String(text || "").replace(/[\r\n]+/g, " ").trim();
      },
      async copyText(text, label) {
        try {
          await navigator.clipboard.writeText(text || "");
          this.toast(label + "已复制");
        } catch (e) {
          this.toast("复制失败，请手动选中文字复制");
        }
      },
      copyNoteCurrent() {
        const isDesc = this.noteTab === "desc";
        this.copyText(isDesc ? this.noteDescText : this.noteImagesText,
          isDesc ? "笔记正文" : "图片文字");
      },
      copyNoteAll() {
        this.copyText(this.noteAllText, "全部文字");
      },
      openViewer(img) {
        if (!img || !img.url) return;
        this.viewer = { url: img.url, role: img.role };
      },
      closeViewer() {
        this.viewer = null;
      },
      // 图文笔记：按图片序号取模型给的版式说明
      planFor(index) {
        const plan = (this.current && this.current.data && this.current.data.image_plan) || [];
        const hit = plan.find((p) => Number(p.index) === Number(index));
        return hit || {};
      },
      async refresh() {
        try {
          const [ov, list] = await Promise.all([
            api("/overview"),
            api("/decompositions" + (this.query ? "?q=" + encodeURIComponent(this.query) : "")),
          ]);
          this.overview = ov;
          this.loginScan = ov.login || {};
          this.items = list.items;
          if (this.route === "deconstruct" && !this.current && this.items.length) {
            await this.selectItem(this.items[0].id);
          }
          if (this.route === "rewrite"
              && (!this.current || this.current.status !== "done")
              && this.items.some((i) => i.status === "done")) {
            await this.selectItem(this.items.find((i) => i.status === "done").id);
          }
          if (this.current && (this.current.status === "processing" || this.current.status === "preparing")) {
            const fresh = this.items.find((i) => i.id === this.current.id);
            if (fresh && fresh.status === "done") await this.selectItem(this.current.id);
          }
        } catch (e) {
          this.toast(e.message);
        }
      },
      async loadSettings() {
        try {
          this.settings = await api("/settings");
          if (this.settings && this.settings.asr && this.settings.asr.model) {
            this.asrModel = this.settings.asr.model;
          }
          const llm = (this.settings && this.settings.llm) || {};
          if (!this.llmForm.base_url) this.llmForm.base_url = llm.base_url || "https://api.deepseek.com";
          if (!this.llmForm.model) this.llmForm.model = llm.model || "deepseek-flash";
          const ocrCfg = (this.settings && this.settings.ocr) || {};
          if (!this.ocrForm.base_url) this.ocrForm.base_url = ocrCfg.base_url || "https://open.bigmodel.cn/api/paas/v4";
          if (!this.ocrForm.model) this.ocrForm.model = ocrCfg.model || "glm-4.6v-flash";
        } catch (e) {}
      },
      go(key) {
        this.route = key;
        window.location.hash = "#/" + key;
        if (key === "deconstruct" || key === "database" || key === "rewrite") this.refresh();
        if (key === "database") this.loadMetrics();
        if (key === "settings") this.loadSettings();
        this.closePalette();
      },
      goRewrite() {
        this.go("rewrite");
      },
      openRewriteItem(id) {
        this.selectItem(id);
      },
      async generateRewrite() {
        if (!this.current || this.rewriteLoading) return;
        this.rewriteLoading = true;
        this.rewriteError = "";
        try {
          await api("/decompositions/" + this.current.id + "/rewrite", { method: "POST" });
          this.current = await api("/decompositions/" + this.current.id);
          this.rewriteView = "parts";
          this.toast("改写稿已生成");
        } catch (e) {
          this.rewriteError = e.message;
          this.toast(e.message);
        } finally {
          this.rewriteLoading = false;
        }
      },
      syncRoute() {
        const key = (window.location.hash || "").replace(/^#\//, "") || "home";
        this.route = PAGES[key] ? key : "home";
      },
      async selectItem(id) {
        try {
          const same = this.current && this.current.id === id;
          this.current = await api("/decompositions/" + id);
          if (!same) {
            const board = (this.current.data && this.current.data.storyboard) || [];
            this.tab = board.length ? "board" : "subtitle";
          }
        } catch (e) {
          this.toast(e.message);
        }
      },
      openFocus(item) {
        if (item.route === "deconstruct") {
          this.go("deconstruct");
          if (this.items.length) this.selectItem(this.items[0].id);
        } else {
          this.go(item.route);
        }
      },
      openTopic() {
        this.go("writing");
      },
      setDbTab(tab) {
        this.dbTab = tab;
        if (tab === "assets") this.refresh();
        if (tab === "account") this.loadMetrics();
      },
      async loadMetrics() {
        try {
          const res = await api("/metrics");
          this.metricsList = res.items || [];
        } catch (e) { this.metricsList = []; }
      },
      openNew() {
        this.form = { title: "", author: "", platform: "视频号", url: "", storyboard: true };
        this.file = null;
        this.modalOpen = true;
        this.closePalette();
        this.$nextTick(() => {
          const el = this.$refs.fileInput;
          if (el) el.value = "";
        });
      },
      async exportData() {
        try {
          const res = await api("/export");
          const blob = new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          const date = new Date().toISOString().slice(0, 10);
          a.href = url;
          a.download = `工作台数据-${date}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          this.toast(`已导出 ${res.counts.decompositions} 条拆解、${res.counts.accounts} 个账号`);
        } catch (e) {
          this.toast("导出失败：" + e.message);
        }
      },
      triggerImport() {
        const el = this.$refs.importInput;
        if (el) { el.value = ""; el.click(); }
      },
      async importData(event) {
        const file = event.target.files && event.target.files[0];
        if (!file) return;
        const text = await file.text();
        let payload;
        try {
          payload = JSON.parse(text);
        } catch (e) {
          this.toast("导入失败：文件不是有效的 JSON");
          return;
        }
        if (!payload || (!payload.decompositions && !payload.accounts)) {
          this.toast("导入失败：不是工作台导出的数据文件");
          return;
        }
        try {
          const res = await api("/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const im = res.imported || {};
          const sk = res.skipped || {};
          const skipped = (sk.decompositions || 0) + (sk.accounts || 0);
          this.toast(`导入完成：拆解 ${im.decompositions} 条、账号 ${im.accounts} 个`
            + (skipped ? `，跳过已存在的 ${skipped} 项` : ""));
          await this.refresh();
          await this.loadAccounts();
        } catch (e) {
          this.toast("导入失败：" + e.message);
        } finally {
          const el = this.$refs.importInput;
          if (el) el.value = "";
        }
      },
      closeNew() {
        this.modalOpen = false;
        this.dragging = false;
      },
      onFile(event) {
        const file = event.target.files && event.target.files[0];
        if (file) this.file = file;
      },
      onDrop(event) {
        this.dragging = false;
        const file = event.dataTransfer.files && event.dataTransfer.files[0];
        if (file) this.file = file;
      },
      async submitNew() {
        if (!this.file && !this.form.url && !this.form.title) {
          this.toast("请上传文件，或至少填写标题");
          return;
        }
        this.submitting = true;
        try {
          const fd = new FormData();
          fd.append("title", this.form.title);
          fd.append("author", this.form.author);
          fd.append("platform", this.form.platform);
          fd.append("url", this.form.url);
          fd.append("storyboard", this.form.storyboard ? "1" : "0");
          if (this.file) fd.append("file", this.file);
          const res = await api("/decompositions", { method: "POST", body: fd });
          this.modalOpen = false;
          this.toast("已开始拆解");
          await this.refresh();
          this.go("deconstruct");
          await this.selectItem(res.id);
          this.startPolling();
        } catch (e) {
          this.toast(e.message);
        } finally {
          this.submitting = false;
        }
      },
      engagement(video) {
        return Number(video && video.likes || 0) + Number(video && video.comments || 0)
          + Number(video && video.shares || 0) + Number(video && video.favorites || 0);
      },
      qualifyValue(video) {
        if (this.filterMetric === "likes") return Number(video.likes || 0);
        if (this.filterMetric === "comments") return Number(video.comments || 0);
        if (this.filterMetric === "favorites") return Number(video.favorites || 0);
        if (this.filterMetric === "total") return this.engagement(video);
        return Number(video.shares || 0);
      },
      async loadPhoneLinks() {
        try {
          const res = await api("/phone/links");
          this.phoneLinks = res.items || [];
        } catch (e) { this.phoneLinks = []; }
      },
      async decomposePhoneLink(link) {
        try {
          const res = await api("/phone/links/" + link.id + "/decompose", { method: "POST" });
          await this.loadPhoneLinks();
          this.decoTab = "video";
          await this.refresh();
          await this.selectItem(res.id);
          this.startPolling();
          this.toast("已开始拆解");
        } catch (e) { this.toast(e.message); }
      },
      async loadAccounts() {
        this.loadSpend();
        try {
          const res = await api("/accounts");
          this.accounts = res.items || [];
          if (this.accountCurrent) {
            const fresh = this.accounts.find((a) => a.id === this.accountCurrent.id);
            if (fresh && fresh.updated_at !== this.accountCurrent.updated_at) {
              await this.selectAccount(fresh.id);
            }
          }
        } catch (e) {
          this.accounts = [];
        }
      },
      async loadSpend() {
        try {
          this.spendToday = await api("/spend/today");
        } catch (e) {
          this.spendToday = null;
        }
      },
      async selectAccount(id) {
        try {
          this.accountCurrent = await api("/accounts/" + id);
          const f = this.accountCurrent.filters || {};
          this.filterDays = Number(f.days || 30);
          this.filterMetric = f.metric || "shares";
          this.filterMin = Number(f.min == null ? 100 : f.min);
          this.accountMessage = "";
        } catch (e) {
          this.toast(e.message);
        }
      },
      async saveFilters() {
        if (!this.accountCurrent) return;
        try {
          await api("/accounts/" + this.accountCurrent.id + "/filters", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ days: this.filterDays, metric: this.filterMetric, min: this.filterMin }),
          });
          this.accountCurrent.filters = { days: this.filterDays, metric: this.filterMetric, min: this.filterMin };
        } catch (e) {
          this.toast(e.message);
        }
      },
      rangeEstimate(mode) {
        const p = this.previewData;
        if (!p || !p.estimates || p.account_id !== (this.accountCurrent && this.accountCurrent.id)) {
          return null;
        }
        return p.estimates[mode || this.collectRange] || null;
      },
      async previewAccount() {
        const nickname = this.accountNickname.trim();
        if (!nickname) { this.toast("先填账号昵称，要一字不差"); return; }
        this.accountBusy = true;
        this.accountMessage = "";
        try {
          const data = await api("/accounts/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nickname }),
          });
          this.previewData = data;
          this.accountNickname = "";
          await this.loadAccounts();
          await this.selectAccount(data.account_id);
          this.toast(`查到基础信息：${data.posts} 条作品，月更约 ${data.per_month} 条`);
        } catch (e) {
          this.accountMessage = e.message;
          this.accountMessageBad = true;
          this.toast(e.message);
        } finally {
          this.accountBusy = false;
        }
      },
      async startCollect() {
        if (!this.accountCurrent || this.accountBusy) return;
        const est = this.rangeEstimate();
        const opt = this.rangeOptions.find((o) => o.key === this.collectRange) || {};
        const costText = est ? `预计 ${est.items} 条、约 $${est.usd}` : "费用按实际翻页计算";
        const ok = window.confirm(
          `将抓取「${opt.label}」的作品：\n\n  ${costText}\n\n确认开始？`
        );
        if (!ok) return;
        this.accountBusy = true;
        try {
          this.accountCurrent = await api(`/accounts/${this.accountCurrent.id}/collect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: this.collectRange }),
          });
          await this.loadAccounts();
          this.toast(`已抓取 ${(this.accountCurrent.videos || []).length} 条`);
        } catch (e) {
          this.toast(e.message);
        } finally {
          this.accountBusy = false;
        }
      },
      async refreshAccount() {
        if (!this.accountCurrent || this.accountBusy) return;
        this.startCollect();
      },
      async analyzeAccount() {
        if (!this.accountCurrent || this.accountBusy) return;
        this.accountBusy = true;
        this.accountMessage = "正在生成账号分析…";
        this.accountMessageBad = false;
        try {
          const res = await api(`/accounts/${this.accountCurrent.id}/analyze`, { method: "POST" });
          this.accountCurrent = { ...this.accountCurrent, analysis: JSON.stringify(res.analysis) };
          this.accountMessage = "";
          this.toast("账号分析已生成");
        } catch (e) {
          this.accountMessage = e.message;
          this.accountMessageBad = true;
        } finally {
          this.accountBusy = false;
        }
      },
      statusLabel(it) {
        if (it.status === "done") return "已完成";
        if (it.status === "preparing") return "取链接中";
        if (it.status === "processing") return "拆解中";
        if (it.status === "failed") return "失败";
        return it.status || "";
      },
      accountVideoAction(v) {
        const d = this.decomposedByVideo[v.id];
        if (d) {
          if (d.status === "done") return { text: "查看拆解", kind: "done" };
          if (d.status === "failed") return { text: "查看并重试", kind: "retry" };
          return { text: d.status === "preparing" ? "取链接中…" : "拆解中…", kind: "busy" };
        }
        return v.link ? { text: "开始拆解", kind: "ready" } : { text: "获取链接", kind: "fetch" };
      },
      async decomposeAccountVideo(video) {
        if (!this.accountCurrent) return;
        // 已经建过的：直接跳过去看，不新建、不再付费
        const existing = this.decomposedByVideo[video.id];
        if (existing) {
          this.decoTab = "video";
          this.go("deconstruct");
          await this.refresh();
          await this.selectItem(existing.id);
          if (existing.status !== "done") this.startPolling();
          return;
        }
        if (this.videoBusyId === video.id) return;
        this.videoBusyId = video.id;
        try {
          const res = await api(
            `/accounts/${this.accountCurrent.id}/videos/${video.id}/decompose`,
            { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
          );
          this.decoTab = "video";
          this.go("deconstruct");
          await this.refresh();
          await this.selectItem(res.id);
          this.startPolling();
          this.toast(res.pending_link ? "已加入，正在获取分享链接" : "已加入视频拆解");
        } catch (e) {
          this.linkPrompt = { open: true, video, text: "", busy: false };
        } finally {
          this.videoBusyId = "";
        }
      },
      closeLinkPrompt() {
        this.linkPrompt = { open: false, video: null, text: "", busy: false };
      },
      async submitVideoLink() {
        const url = (this.linkPrompt.text || "").trim();
        if (!/^https?:\/\//.test(url)) { this.toast("请粘贴完整的分享链接"); return; }
        const video = this.linkPrompt.video || {};
        const account = this.accountCurrent || {};
        this.linkPrompt.busy = true;
        try {
          const fd = new FormData();
          fd.append("title", (video.text || "").slice(0, 60) || "账号作品");
          fd.append("author", account.name || "");
          fd.append("platform", account.platform || "视频号");
          fd.append("url", url);
          fd.append("storyboard", "1");
          fd.append("account", account.name || "");
          const res = await api("/decompositions", { method: "POST", body: fd });
          this.closeLinkPrompt();
          this.decoTab = "video";
          await this.refresh();
          await this.selectItem(res.id);
          this.startPolling();
          this.toast("已加入视频拆解，后台解析中");
        } catch (e) {
          this.toast(e.message);
        } finally {
          this.linkPrompt.busy = false;
        }
      },
      async submitAccount() {
        const name = this.accountForm.name.trim();
        const links = this.accountForm.links
          .split(/[\s\n]+/).map((s) => s.trim()).filter((s) => /^https?:\/\//.test(s));
        if (!name) { this.toast("先填账号名称"); return; }
        if (!links.length) { this.toast("至少粘贴 1 条视频链接"); return; }
        if (links.length > 30) { this.toast("一次最多 30 条，分批提交"); return; }
        this.accountSubmitting = true;
        let ok = 0;
        let fail = 0;
        for (let i = 0; i < links.length; i += 1) {
          this.accountProgress = `正在提交 ${i + 1}/${links.length}`;
          const fd = new FormData();
          fd.append("title", "");
          fd.append("author", name);
          fd.append("platform", this.accountForm.platform);
          fd.append("url", links[i]);
          fd.append("storyboard", this.accountForm.storyboard ? "1" : "0");
          fd.append("account", name);
          try {
            await api("/decompositions", { method: "POST", body: fd });
            ok += 1;
          } catch (e) {
            fail += 1;
          }
        }
        this.accountProgress = "";
        this.accountSubmitting = false;
        this.accountForm.links = "";
        await this.refresh();
        this.toast(`已提交 ${ok} 条${fail ? `，失败 ${fail} 条` : ""}，后台逐条下载、转写`);
      },
      fmtCount(value) {
        const n = Number(value || 0);
        if (!n) return "0";
        if (n >= 10000) return `${(n / 10000).toFixed(1)}万`;
        return String(n);
      },
      openFromAccount(id) {
        this.decoTab = "video";
        this.go("deconstruct");
        this.selectItem(id);
      },
      async linkLogin() {
        if (this.linkScanning) return;
        try {
          const res = await api("/link/login", { method: "POST" });
          if (!res.ok) {
            this.toast(res.message || "无法开始登录");
            return;
          }
          this.linkScanning = true;
          this.toast("已打开浏览器，请用微信扫码登录腾讯元宝");
          for (let i = 0; i < 160; i++) {
            await new Promise((r) => setTimeout(r, 2000));
            const st = await api("/link/status");
            if (st.status === "ok") {
              this.linkScanning = false;
              this.toast("元宝登录成功，可以解析视频号链接了");
              await this.loadSettings();
              return;
            }
            if (st.status === "failed") {
              this.linkScanning = false;
              this.toast(st.message || "登录失败");
              await this.loadSettings();
              return;
            }
          }
          this.linkScanning = false;
        } catch (e) {
          this.linkScanning = false;
          this.toast(e.message);
        }
      },
      async saveLlm() {
        this.savingLlm = true;
        this.llmMessage = "";
        try {
          const payload = {
            llm_base_url: this.llmForm.base_url.trim(),
            llm_model_name: this.llmForm.model.trim(),
          };
          if (this.llmForm.api_key.trim()) payload.llm_api_key = this.llmForm.api_key.trim();
          await api("/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          this.llmForm.api_key = "";
          this.llmTest = "";
          await this.loadSettings();
          this.toast("已保存，正在测试连接");
          await this.testLlm();
        } catch (e) { this.toast(e.message); }
        finally { this.savingLlm = false; }
      },
      async testLlm() {
        this.testingLlm = true;
        this.llmMessage = "";
        try {
          const res = await api("/llm/test", { method: "POST" });
          if (res.available) {
            this.llmTest = "ok";
            this.llmMessageBad = false;
            this.llmMessage = "连接正常 · " + res.model;
          } else {
            this.llmTest = "fail";
            this.llmMessageBad = true;
            this.llmMessage = res.error || (res.key_set ? "连接失败" : "还没有填写 API Key");
          }
        } catch (e) {
          this.llmTest = "fail";
          this.llmMessageBad = true;
          this.llmMessage = e.message;
        } finally {
          this.testingLlm = false;
        }
      },
      async saveOcr() {
        this.savingOcr = true;
        this.ocrMessage = "";
        try {
          const payload = {
            ocr_base_url: this.ocrForm.base_url.trim(),
            ocr_model: this.ocrForm.model.trim(),
          };
          if (this.ocrForm.api_key.trim()) payload.ocr_api_key = this.ocrForm.api_key.trim();
          await api("/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          this.ocrForm.api_key = "";
          this.ocrTest = "";
          await this.loadSettings();
          this.toast("OCR 配置已保存，正在测试");
          await this.testOcr();
        } catch (e) { this.toast(e.message); }
        finally { this.savingOcr = false; }
      },
      async testOcr() {
        this.testingOcr = true;
        this.ocrMessage = "";
        try {
          const res = await api("/ocr/test", { method: "POST" });
          if (res.available) {
            this.ocrTest = "ok";
            this.ocrMessageBad = false;
            this.ocrMessage = "连接正常 · " + res.model;
          } else {
            this.ocrTest = "fail";
            this.ocrMessageBad = true;
            this.ocrMessage = res.error || (res.key_set ? "连接失败" : "还没有填写 API Key");
          }
        } catch (e) {
          this.ocrTest = "fail";
          this.ocrMessageBad = true;
          this.ocrMessage = e.message;
        } finally {
          this.testingOcr = false;
        }
      },
      async saveDatax() {
        const key = this.dataxForm.api_key.trim();
        if (!key) { this.toast("请先粘贴 DataXAPI Key"); return; }
        this.savingDatax = true;
        try {
          await api("/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ dataxapi_api_key: key }),
          });
          this.dataxForm.api_key = "";
          this.dataxMsg = "";
          await this.loadSettings();
          this.toast("DataXAPI Key 已保存到本机");
        } catch (e) { this.toast(e.message); }
        finally { this.savingDatax = false; }
      },
      async testDatax() {
        this.testingDatax = true;
        this.dataxMsg = "";
        try {
          const res = await api("/dataxapi/probe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nickname: this.dataxNickname.trim() }),
          });
          this.dataxMsgBad = false;
          this.dataxMsg = res.username
            ? `已拿到内部账号：${res.username.slice(0, 18)}…（原始结果已存 data\\exports）`
            : "接口通了，但没搜到账号，换一字不差的昵称再试";
        } catch (e) {
          this.dataxMsgBad = true;
          this.dataxMsg = e.message;
        } finally {
          this.testingDatax = false;
        }
      },
      async saveTikhub() {
        const key = this.tikhubForm.api_key.trim();
        if (!key) { this.toast("请先粘贴 TikHub API Key"); return; }
        this.savingTikhub = true;
        try {
          await api("/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tikhub_api_key: key }),
          });
          this.tikhubForm.api_key = "";
          this.tikhubMsg = "";
          await this.loadSettings();
          this.toast("TikHub Key 已保存到本机");
        } catch (e) { this.toast(e.message); }
        finally { this.savingTikhub = false; }
      },
      async testTikhub() {
        this.testingTikhub = true;
        this.tikhubMsg = "";
        try {
          const res = await api("/tikhub/probe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ channel_id: this.tikhubId.trim() }),
          });
          this.tikhubMsgBad = false;
          this.tikhubMsg = res.username
            ? `已拿到内部账号：${res.username.slice(0, 18)}…（原始结果已存 data\\exports）`
            : "接口通了，但没解析出 username，看导出文件";
        } catch (e) {
          this.tikhubMsgBad = true;
          this.tikhubMsg = e.message;
        } finally {
          this.testingTikhub = false;
        }
      },
      async saveAsrModel() {
        try {
          await api("/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ asr_model_name: this.asrModel }),
          });
          this.toast("已切换转写模型，下一次转写生效");
          await this.loadSettings();
        } catch (e) { this.toast(e.message); }
      },
      async transcribeAgain() {
        const s = this.sourceInfo;
        if (!s) return;
        try {
          const res = await api("/sources/" + s.id + "/transcribe", { method: "POST" });
          if (!res.ok) {
            this.toast(res.message || "无法开始转写");
            return;
          }
          this.toast("已开始转写");
          await this.selectItem(this.current.id);
        } catch (e) { this.toast(e.message); }
      },
      async rerun() {
        if (!this.current) return;
        try {
          await api("/decompositions/" + this.current.id + "/rerun", { method: "POST" });
          this.current.status = "processing";
          this.toast("正在重新拆解");
          this.startPolling();
        } catch (e) { this.toast(e.message); }
      },
      async removeCurrent() {
        if (!this.current) return;
        if (!window.confirm("删除这条拆解？原始文件也会一并删除，且不可恢复。")) return;
        try {
          await api("/decompositions/" + this.current.id, { method: "DELETE" });
          this.current = null;
          this.toast("已删除");
          await this.refresh();
        } catch (e) { this.toast(e.message); }
      },
      async toggleDemo() {
        if (!this.settings) return;
        this.settings.demo_mode = !this.settings.demo_mode;
        try {
          await api("/settings", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ demo_mode: this.settings.demo_mode }),
          });
          this.toast(this.settings.demo_mode ? "已切换到演示模式" : "已切换到真实模式");
        } catch (e) { this.toast(e.message); }
      },
      async startScan() {
        if (this.scanning) return;
        if (this.syncing) {
          this.toast("正在同步数据，稍后再扫码");
          return;
        }
        try {
          const res = await api("/login/scan", { method: "POST" });
          if (!res.ok) {
            this.toast(res.message || "无法开始扫码");
            return;
          }
          this.scanning = true;
          this.toast("已打开浏览器，请扫码登录");
          for (let i = 0; i < 170; i++) {
            await new Promise((r) => setTimeout(r, 2000));
            const st = await api("/login/status");
            if (st.status === "ok") {
              this.scanning = false;
              this.toast("登录成功，可以同步数据了");
              await this.refresh();
              this.loadSettings();
              return;
            }
            if (st.status === "failed") {
              this.scanning = false;
              this.toast(st.message || "扫码没有完成");
              await this.refresh();
              return;
            }
          }
          this.scanning = false;
        } catch (e) {
          this.scanning = false;
          this.toast(e.message || "扫码失败");
        }
      },
      async syncData() {
        if (this.syncing || this.scanning) return;
        this.syncing = true;
        this.toast("已开始同步，请稍候");
        try {
          const started = await api("/sync/run", { method: "POST" });
          if (!started.ok) {
            this.toast(started.message || "无法开始同步");
            return;
          }
          for (let i = 0; i < 80; i++) {
            await new Promise((r) => setTimeout(r, 1500));
            const st = await api("/sync/status");
            if (!st.running) {
              await this.refresh();
              if (st.status === "ok") this.toast("同步完成：" + st.date);
              else if (st.status === "login_expired") this.toast("登录已过期，需要重新扫码");
              else this.toast("同步失败：" + (st.message || "未知原因"));
              break;
            }
          }
        } catch (e) {
          this.toast(e.message || "同步失败");
        } finally {
          this.syncing = false;
        }
      },
      copyScript() {
        if (!this.current) return;
        const text = this.fullScriptText;
        navigator.clipboard.writeText(text).then(
          () => this.toast("口播稿已复制"),
          () => this.toast("复制失败，请手动选择")
        );
      },
      copyTranscript() {
        const s = this.sourceInfo || {};
        const text = this.subView === "punctuated" ? (s.punctuated_text || "")
          : (s.transcript || "");
        if (!text) return;
        navigator.clipboard.writeText(text).then(
          () => this.toast("字幕全文已复制"),
          () => this.toast("复制失败，请手动选择")
        );
      },
      toast(message) {
        this.toastMsg = message;
        clearTimeout(this.toastTimer);
        this.toastTimer = setTimeout(() => (this.toastMsg = ""), 2400);
      },
      openPalette() {
        this.paletteOpen = true;
        this.paletteQuery = "";
        this.paletteIndex = 0;
        this.$nextTick(() => this.$refs.paletteInput && this.$refs.paletteInput.focus());
      },
      closePalette() { this.paletteOpen = false; },
      paletteMove(step) {
        const n = this.paletteResults.length;
        if (!n) return;
        this.paletteIndex = (this.paletteIndex + step + n) % n;
      },
      paletteRun() {
        const cmd = this.paletteResults[this.paletteIndex];
        if (cmd) this.runCommand(cmd);
      },
      runCommand(cmd) {
        this.closePalette();
        if (cmd && cmd.run) cmd.run();
      },
      startPolling() {
        if (this.pollTimer) return;
        this.pollTimer = setInterval(async () => {
          const busy = this.processingCount > 0 || (this.current && (this.current.status === "processing" || this.current.status === "preparing"));
          const listening = this.current && this.current.source && this.current.source.status === "transcribing";
          if (!busy && !listening) return;
          await this.refresh();
          if (listening) await this.selectItem(this.current.id);
          if (this.current && (this.current.status === "processing" || this.current.status === "preparing")) {
            const fresh = this.items.find((i) => i.id === this.current.id);
            if (fresh && fresh.status === "done") await this.selectItem(this.current.id);
          }
        }, 2200);
      },
      relative(iso) {
        if (!iso) return "";
        const diff = Date.now() - new Date(iso).getTime();
        const min = Math.floor(diff / 60000);
        if (min < 1) return "刚刚";
        if (min < 60) return min + " 分钟前";
        const hr = Math.floor(min / 60);
        if (hr < 24) return hr + " 小时前";
        const day = Math.floor(hr / 24);
        if (day < 30) return day + " 天前";
        return new Date(iso).toLocaleDateString("zh-CN");
      },
      clock(iso) {
        if (!iso) return "—";
        const d = new Date(iso);
        return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
      },
      fmtDateTime(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        const p = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
      },
      fmtNum(v) {
        return Number(v || 0).toLocaleString("zh-CN");
      },
      fmtSeconds(total) {
        const s = Math.max(0, Math.round(total || 0));
        return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
      },
      statusText(status) {
        return {
          processing: "拆解中", done: "已完成", failed: "失败",
          ready: "未转写", transcribing: "转写中", transcribed: "已转写", transcribe_failed: "转写失败",
        }[status] || status;
      },
    },
    mounted() {
      this.syncRoute();
      this.refresh();
      this.loadSettings();
      this.startPolling();
      setInterval(() => (this.now = new Date()), 60000);
      window.addEventListener("hashchange", () => {
        this.syncRoute();
        if (this.route === "deconstruct" || this.route === "database") this.refresh();
      });
      window.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
          e.preventDefault();
          if (this.paletteOpen) this.closePalette();
          else this.openPalette();
        }
        if (e.key === "Escape") {
          this.closePalette();
          this.closeNew();
        }
      });
    },
    template: `
<div class="shell">
  <aside class="rail">
    <div class="brand">
      <div class="brand-mark">IP</div>
      <div class="brand-text">
        <strong>运营工作台</strong>
        <span>单人 · 本地运行</span>
      </div>
    </div>

    <nav class="nav">
      <div class="nav-group" v-for="group in navGroups" :key="group.label">
        <div class="nav-label">{{ group.label }}</div>
        <button v-for="item in group.items" :key="item.key"
                class="nav-item" :class="{ active: route === item.key }"
                @click="go(item.key)">
          <span class="nav-icon" v-html="icons[item.icon]"></span>
          <span>{{ item.label }}</span>
          <span class="nav-badge" v-if="item.key === 'deconstruct' && processingCount">{{ processingCount }}</span>
        </button>
      </div>
    </nav>

    <div class="rail-foot">
      <div class="mode">
        <span class="dot" :class="{ demo: isDemo && !metrics.real }"></span>
        {{ metrics.real ? '真实数据' : (isDemo ? '演示数据' : '真实模式') }}
      </div>
      <div class="rail-meta">127.0.0.1:8741 · v{{ (settings && settings.version) || '0.3.0' }}</div>
    </div>
  </aside>

  <main class="main">
    <header class="topbar">
      <div class="crumb">工作台 / <b>{{ sectionLabel }}</b></div>
      <div class="topbar-right">
        <span class="date">{{ todayLabel }}</span>
        <button class="kbd" @click="openPalette">Ctrl K</button>
        <div class="avatar">我</div>
      </div>
    </header>

    <div class="content">

      <!-- 首页 -->
      <section v-if="route === 'home'" class="page" :key="route">
        <header class="home-head">
          <div>
            <h1 class="greeting">{{ greeting }}，今天也<em>按自己的节奏</em>来。</h1>
            <p class="sub">{{ recentHeadline }}</p>
          </div>
          <div class="head-actions">
            <button class="btn warn" v-if="needScan || scanning" :disabled="scanning" @click="startScan">{{ scanning ? '等待扫码…' : '重新扫码' }}</button>
            <button class="btn" :disabled="syncing || scanning" @click="syncData">{{ syncing ? '同步中…' : '同步数据' }}</button>
            <button class="btn btn-primary" @click="openNew">＋ 新建拆解</button>
          </div>
        </header>

        <div class="home-grid">
          <div class="col">
            <section class="hero">
              <div class="hero-ring"></div>
              <div class="hero-ring-2"></div>
              <div>
                <div class="hero-label">粉丝总数</div>
                <div class="hero-mid">
                  <div class="hero-number">{{ metrics.followers }}</div>
                  <span class="hero-delta" :class="{ down: metrics.net < 0 }" v-if="metrics.real">{{ metrics.newFollowers }}</span>
                  <span class="hero-delta" v-else-if="isDemo">↑ {{ metrics.newFollowers }} 昨日新增</span>
                  <span class="hero-delta" v-else>{{ metrics.newFollowers }}</span>
                </div>
              </div>
              <div class="hero-foot">
                <span>{{ (overview && overview.account && overview.account.nickname) || '视频号 · 运营账号' }}</span>
                <span>{{ metrics.real ? '数据截至 ' + metrics.date : dataNote }}</span>
              </div>
            </section>

            <section class="card">
              <div class="card-head">
                <h2>今日重点</h2>
                <span class="note"><span class="tag peach">演示</span>3 件 · 约 2 小时</span>
              </div>
              <ul class="focus">
                <li v-for="(item, i) in focusItems" :key="i">
                  <div class="focus-ico">{{ ['◫','✎','▦'][i] || '•' }}</div>
                  <div class="focus-main">
                    <div class="focus-title">{{ item.title }}</div>
                    <div class="focus-meta">{{ item.meta }}</div>
                  </div>
                  <span class="tag" :class="item.tagClass">{{ item.tag }}</span>
                  <button class="btn" @click="openFocus(item)">{{ item.action }}</button>
                </li>
              </ul>
            </section>

            <section class="card">
              <div class="card-head">
                <h2>今天选题</h2>
                <span class="note"><span class="tag peach">演示</span>3 条 · 拆解 / 抓取 / 手动</span>
              </div>
              <ul class="focus">
                <li v-for="(item, i) in topicItems" :key="i">
                  <div class="focus-ico">✦</div>
                  <div class="focus-main">
                    <div class="focus-title">{{ item.title }}</div>
                    <div class="focus-meta">{{ item.meta }}</div>
                  </div>
                  <span class="tag" :class="item.tagClass">{{ item.tag }}</span>
                  <button class="btn" @click="openTopic">去写稿</button>
                </li>
              </ul>
            </section>
          </div>

          <div class="col">
            <section class="card">
              <div class="card-head">
                <h2>昨日数据</h2>
                <span class="note">{{ dataNote }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">总阅读</span>
                <span><span class="metric-value">{{ metrics.totalViews }}</span><span class="metric-delta" v-if="!metrics.real && isDemo">+18%</span></span>
              </div>
              <div class="metric">
                <span class="metric-label">单条最高</span>
                <span>
                  <span class="metric-value">{{ metrics.topViews }}</span>
                  <em class="metric-sub" v-if="metrics.topTitle">{{ metrics.topTitle }}</em>
                </span>
              </div>
              <div class="metric">
                <span class="metric-label">互动率</span>
                <span><span class="metric-value">{{ metrics.engagement }}</span><span class="metric-delta down" v-if="metrics.engagementDelta">{{ metrics.engagementDelta }}</span></span>
              </div>
            </section>

            <section class="card">
              <div class="card-head">
                <h2>本周待办</h2>
                <span class="note"><span class="tag peach">演示</span>还差 2 件</span>
              </div>
              <ul class="week">
                <li v-for="(w, i) in weekItems" :key="i">
                  <span class="week-day">{{ w.day }}</span>
                  <span class="week-dot" :class="w.dot"></span>
                  <span class="week-text" v-html="w.text"></span>
                </li>
              </ul>
            </section>

            <div class="footnote">
              <span v-if="dataHint" style="color: var(--warn, #B4552F)">{{ dataHint }}</span>
              <span v-else>{{ metrics.real ? '数据来自视频号后台 · 每日同步' : (isDemo ? '演示数据 · 未接入自动抓取' : '尚未同步') }}</span>
              <a @click="go('database')">查看数据详情 →</a>
            </div>
          </div>
        </div>
      </section>

      <!-- 对标拆解 -->
      <section v-else-if="route === 'deconstruct'" class="page" :key="route">
        <header class="page-head">
          <div>
            <h1>对标拆解</h1>
            <p>把一条视频拆成钩子、留存、金句和可拍的镜头。</p>
          </div>
          <div class="head-actions">
            <button class="btn" :disabled="linkScanning" @click="linkLogin">{{ linkScanning ? '等待扫码…' : '元宝登录 / 续期' }}</button>
            <button class="btn" @click="exportData">导出数据</button>
            <button class="btn" @click="triggerImport">导入数据</button>
            <input ref="importInput" type="file" accept=".json" style="display:none" @change="importData" />
            <button class="btn" @click="refresh">刷新</button>
            <button class="btn btn-primary" @click="openNew">＋ 新建拆解</button>
          </div>
        </header>

        <div class="mode-switch">
          <button class="chip" :class="{ active: decoTab === 'video' }" @click="decoTab = 'video'">视频拆解</button>
          <button class="chip" :class="{ active: decoTab === 'account' }" @click="decoTab = 'account'; loadAccounts(); loadPhoneLinks()">账号拆解</button>
        </div>

        <div v-if="decoTab === 'video'" class="deco-layout">
          <aside class="card queue">
            <input class="input" v-model="query" placeholder="搜索标题" />
            <div class="filters">
              <button class="chip" :class="{ active: listFilter === 'all' }" @click="listFilter = 'all'">全部 {{ items.length }}</button>
              <button class="chip" :class="{ active: listFilter === 'done' }" @click="listFilter = 'done'">已完成 {{ doneCount }}</button>
              <button class="chip" :class="{ active: listFilter === 'processing' }" @click="listFilter = 'processing'">进行中 {{ processingCount }}</button>
            </div>
            <div class="queue-list">
              <button v-for="it in filteredItems" :key="it.id"
                      class="queue-item" :class="{ active: current && current.id === it.id }"
                      @click="selectItem(it.id)">
                <span class="queue-time">{{ clock(it.created_at) }}</span>
                <span class="light" :class="it.status"></span>
                <span>
                  <span class="queue-title">{{ it.title }}</span>
                  <span class="queue-meta">
                    <em class="status-tag" :class="it.status">{{ statusLabel(it) }}</em>
                    {{ it.platform || '—' }}<template v-if="it.hook_score"> · 钩子 {{ it.hook_score }}</template>
                  </span>
                </span>
              </button>
              <div v-if="!filteredItems.length" class="empty-state">
                <p>还没有记录。点右上角新建一条。</p>
              </div>
            </div>
          </aside>

          <div class="detail">
            <div v-if="!current" class="card empty-state">
              <div class="ico">◫</div>
              <h2>选一条开始</h2>
              <p>从左边选一条拆解，或者新建一条。上传视频后，这里会出现它的时间轴和场记单。</p>
              <button class="btn btn-primary" @click="openNew">新建拆解</button>
            </div>

            <div v-else-if="current.status === 'processing' || current.status === 'preparing'" class="card scene">
              <header class="scene-head">
                <div>
                  <div class="scene-kicker">{{ current.data.platform || current.platform || '视频号' }}</div>
                  <h2 class="scene-title">{{ current.title }}</h2>
                  <div class="scene-meta"><span>{{ fmtDateTime(current.created_at) }}</span></div>
                </div>
              </header>
              <div class="processing-box">
                <div class="processing-line"></div>
                <p class="processing-label">{{ current.status === 'preparing' ? '正在获取分享链接' : '正在转写与结构化' }}</p>
                <ol class="processing-steps">
                  <li class="done">已接收素材</li>
                  <li :class="current.status === 'preparing' ? 'now' : 'done'">获取分享链接</li>
                  <li :class="current.status === 'preparing' ? '' : 'now'">转写与分段</li>
                  <li>结构拆解</li>
                </ol>
              </div>
            </div>

            <div v-else-if="current.status === 'failed'" class="card scene">
              <header class="scene-head">
                <div>
                  <div class="scene-kicker">拆解失败</div>
                  <h2 class="scene-title">{{ current.title }}</h2>
                  <div class="scene-meta"><span>{{ fmtDateTime(current.updated_at) }}</span></div>
                </div>
                <div class="scene-actions">
                  <button class="btn btn-sm" @click="rerun">重新拆解</button>
                  <button class="btn btn-sm btn-danger" @click="removeCurrent">删除</button>
                </div>
              </header>
              <p class="sub-hint">{{ (current.data && current.data.error) || '未知原因' }}</p>
              <p class="sub-hint">如果是字幕没拿到，先到「原始字幕」标签检查转写状态；转写完成后点「重新拆解」。</p>
            </div>

            <article v-else class="card scene">
              <header class="scene-head">
                <div>
                  <div class="scene-kicker">
                    {{ current.data.platform || current.platform || '—' }}<template v-if="current.data.author"> / {{ current.data.author }}</template>
                  </div>
                  <h2 class="scene-title">{{ current.title }}</h2>
                  <div class="scene-meta">
                    <span>{{ fmtDateTime(current.created_at) }}</span>
                    <span v-if="current.is_demo" class="flag">演示数据</span>
                    <span v-else-if="current.data && current.data.engine">{{ current.data.engine }}</span>
                  </div>
                </div>
                <div class="scene-actions">
                  <button class="btn btn-sm btn-primary" @click="goRewrite">去改写</button>
                  <button class="btn btn-sm" @click="rerun">重新拆解</button>
                  <button class="btn btn-sm btn-danger" @click="removeCurrent">删除</button>
                </div>
              </header>

              <template v-if="isNote">
                <table class="sheet-table">
                  <tbody>
                    <tr><th>钩子</th><td>{{ current.data.title_analysis && current.data.title_analysis.hook }}</td></tr>
                    <tr><th>公式</th><td>{{ current.data.title_analysis && current.data.title_analysis.formula }}</td></tr>
                    <tr>
                      <th>关键词</th>
                      <td>
                        <div class="tag-row">
                          <span class="tag green" v-for="k in noteKeywords" :key="k">{{ k }}</span>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <th>标签</th>
                      <td>
                        <div class="tag-row">
                          <span class="tag" v-for="t in noteTags" :key="t">{{ t }}</span>
                        </div>
                      </td>
                    </tr>
                    <tr><th>评论引导</th><td>{{ current.data.conversion && current.data.conversion.comment_hook }}</td></tr>
                    <tr><th>私信引导</th><td>{{ current.data.conversion && current.data.conversion.dm_hook }}</td></tr>
                    <tr><th>整体号召</th><td>{{ current.data.conversion && current.data.conversion.cta }}</td></tr>
                    <tr>
                      <th>注意点</th>
                      <td><span class="sheet-note" v-for="(r, i) in (current.data.risks || [])" :key="i">{{ r }}</span></td>
                    </tr>
                  </tbody>
                </table>

                <div class="block-head" style="margin-top: 22px"><span>图文结构</span></div>
                <table class="sheet-table note-structure">
                  <thead><tr><th>图</th><th>要点分析</th></tr></thead>
                  <tbody>
                    <tr v-for="img in noteImages" :key="img.index">
                      <td class="note-role">{{ img.role }}</td>
                      <td class="note-analysis">{{ planFor(img.index).summary || '—' }}</td>
                    </tr>
                  </tbody>
                </table>

                <div class="block-head" style="margin-top: 22px">
                  <span>图片（{{ noteImages.length }} 张 · 点击看大图）</span>
                </div>
                <div class="note-grid">
                  <button type="button" class="note-thumb" v-for="img in noteImages" :key="img.index"
                          @click="openViewer(img)">
                    <img v-if="img.url" :src="img.url" :alt="img.role" loading="lazy" />
                    <span v-else class="note-missing">{{ img.role }}没下载到</span>
                  </button>
                </div>

                <div class="block-head note-origin-head" style="margin-top: 28px">
                  <span>原文</span>
                  <button class="btn btn-sm" @click="copyNoteAll">复制全部文字</button>
                </div>

                <div class="tabs note-tabs">
                  <button class="tab" :class="{ active: noteTab === 'desc' }" @click="noteTab = 'desc'">笔记正文</button>
                  <button class="tab" :class="{ active: noteTab === 'images' }" @click="noteTab = 'images'">图片文字</button>
                  <button class="btn btn-sm note-copy" @click="copyNoteCurrent">
                    复制{{ noteTab === 'desc' ? '正文' : '图片文字' }}
                  </button>
                </div>

                <div v-if="noteTab === 'desc'" class="note-pane">
                  <div class="note-label">标题</div>
                  <h3 class="note-title-text">{{ current.title || current.data.title || '（无标题）' }}</h3>
                  <div class="note-label">正文</div>
                  <p class="note-body-text" v-if="noteDescClean">{{ noteDescClean }}</p>
                  <p class="note-body-text note-empty" v-else>（这条笔记没有正文）</p>
                </div>

                <div v-else class="note-pane note-pane-list">
                  <details class="note-piece" v-for="img in noteImages" :key="img.index">
                    <summary>
                      <span class="note-piece-role">{{ img.role }}</span>
                      <span class="note-piece-peek">{{ oneLine(img.title) || '（无标题）' }}</span>
                    </summary>
                    <template v-if="img.title">
                      <div class="note-label">标题</div>
                      <div class="note-piece-title">{{ img.title }}</div>
                    </template>
                    <template v-if="img.paragraphs.length">
                      <div class="note-label">正文</div>
                      <p class="note-piece-body" v-for="(p, i) in img.paragraphs" :key="i">{{ p }}</p>
                    </template>
                    <p class="note-piece-body note-empty"
                       v-else-if="!img.text">{{ img.error ? ('下载失败：' + img.error) : '没有识别到文字' }}</p>
                  </details>
                </div>

                <div v-if="viewer" class="lightbox" @click="closeViewer">
                  <img :src="viewer.url" :alt="viewer.role" />
                  <div class="lightbox-cap">{{ viewer.role }}</div>
                </div>
              </template>

              <section class="timeline-block" v-if="!isNote">
                <div class="block-head">
                  <span>结构分段（推断）</span>
                  <span class="mono">{{ retentionSummary }}</span>
                </div>
                <div class="timeline-track">
                  <div v-for="(s, i) in timeline" :key="i"
                       class="timeline-seg"
                       :title="s.label + (s.move ? ' · ' + s.move : '')"
                       :style="{ flexGrow: s.span, flexBasis: 0 }">
                    <span class="seg-mark"></span>
                    <span class="seg-label">{{ fmtSeconds(s.start) }}</span>
                  </div>
                </div>
                <div class="timeline-scale"><span>0:00</span><span>{{ scaleEnd }}</span></div>
              </section>

              <table class="sheet-table" v-if="!isNote">
                <tbody>
                  <tr>
                    <th>钩子</th>
                    <td>
                      <strong>{{ current.data.hook && current.data.hook.text }}</strong>
                      <span class="score" v-if="current.data.hook && current.data.hook.score">{{ current.data.hook.score }}</span>
                      <span class="sheet-note">{{ current.data.hook && current.data.hook.mechanism }}</span>
                      <span class="sheet-note" v-if="current.data.hook && current.data.hook.why">{{ current.data.hook.why }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th>选题</th>
                    <td>
                      {{ current.data.topic && current.data.topic.text }}
                      <span class="sheet-note">角度：{{ current.data.topic && current.data.topic.angle }}</span>
                      <span class="sheet-note">受众：{{ current.data.topic && current.data.topic.audience }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th>情绪</th>
                    <td>
                      {{ current.data.emotion && current.data.emotion.primary }}
                      <div class="tag-row">
                        <span class="tag green" v-for="e in (current.data.emotion && current.data.emotion.curve) || []" :key="e">{{ e }}</span>
                      </div>
                      <span class="sheet-note">{{ current.data.emotion && current.data.emotion.notes }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th>剪辑</th>
                    <td>
                      <template v-if="current.data.pacing && current.data.pacing.shots">
                        {{ current.data.pacing.shots }} 个镜头 · 平均 {{ current.data.pacing.avg_shot }}
                        <span class="sheet-note">{{ current.data.pacing.rhythm }}</span>
                        <span class="sheet-note">{{ current.data.pacing.notes }}</span>
                      </template>
                      <span v-else class="sheet-note">真实切镜与剪辑指标将在视频画面分析接入后生成（下一步）。</span>
                    </td>
                  </tr>
                  <tr>
                    <th>转化</th>
                    <td>
                      {{ current.data.conversion && current.data.conversion.goal }}
                      <span class="sheet-note">{{ current.data.conversion && current.data.conversion.device }}</span>
                      <span class="sheet-note">{{ current.data.conversion && current.data.conversion.cta }}</span>
                    </td>
                  </tr>
                  <tr>
                    <th>金句</th>
                    <td>
                      <div class="quote" v-for="(q, i) in (current.data.quotes || [])" :key="i">{{ q.text }}</div>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div class="block-head" style="margin-top: 22px" v-if="!isNote">
                <span>可拍摄标题</span>
              </div>
              <div class="tag-row" v-if="!isNote">
                <span class="tag green" v-for="t in (current.data.title_options || [])" :key="t">{{ t }}</span>
              </div>

              <div class="tabs" v-if="!isNote">
                <button class="tab" :class="{ active: tab === 'subtitle' }" @click="tab = 'subtitle'">原始字幕</button>
                <button class="tab" :class="{ active: tab === 'board' }" @click="tab = 'board'">分镜</button>
              </div>

              <div v-if="!isNote && tab === 'subtitle'" class="tab-body">
                <div class="sub-head">
                  <span class="sub-state" :class="subtitleState.kind">
                    <template v-if="subtitleState.kind === 'running'">正在转写<template v-if="subtitleState.progress != null"> · {{ subtitleState.progress }}%</template></template>
                    <template v-else-if="subtitleState.kind === 'done'">{{ subtitleState.demo ? '演示字幕' : '转写完成' }}</template>
                    <template v-else-if="subtitleState.kind === 'failed'">转写失败</template>
                    <template v-else-if="subtitleState.kind === 'no_file'">没有本地视频文件</template>
                    <template v-else-if="subtitleState.kind === 'ready'">还没转写</template>
                    <template v-else>没有字幕</template>
                  </span>
                  <span class="sub-meta">{{ subtitleMetaLine }}</span>
                  <button class="btn btn-sm" v-if="sourceInfo && sourceInfo.has_file"
                          :disabled="subtitleState.kind === 'running'" @click="transcribeAgain">
                    {{ subtitleState.kind === 'running' ? '转写中…' : (subtitleState.kind === 'done' ? '重新转写' : '开始转写') }}
                  </button>
                </div>
                <p class="sub-hint" v-if="subtitleState.kind === 'running'">{{ (sourceInfo && sourceInfo.transcript) ? '正在重新转写，下面是上一次的字幕；完成后会替换。' : '音频越长用时越久；可以离开这一页，转写会在后台继续。' }}</p>
                <p class="sub-hint" v-else-if="subtitleState.kind === 'failed'">{{ subtitleState.error }}</p>
                <p class="sub-hint" v-else-if="subtitleState.kind === 'no_file'">链接导入在第 5 阶段接入，目前只有上传的视频文件可以转写。</p>
                <p class="sub-hint" v-else-if="subtitleState.kind === 'ready'">这条素材有本地文件，点「开始转写」。首次使用某个模型时会先下载模型（small 约 460MB，medium 约 1.5GB），需要等几分钟。</p>
                <p class="sub-hint" v-if="sourceInfo && sourceInfo.proofread_changes && sourceInfo.proofread_changes.length">
                  校对修改 {{ sourceInfo.proofread_changes.length }} 处：{{ sourceInfo.proofread_changes.slice(0, 6).join('；') }}<span v-if="sourceInfo.proofread_changes.length > 6"> 等</span>
                </p>
                <div class="view-toggle" v-if="sourceInfo && sourceInfo.transcript">
                  <button class="chip" :class="{ active: subView === 'segments' }" @click="subView = 'segments'">时间轴</button>
                  <button class="chip" :class="{ active: subView === 'full' }" @click="subView = 'full'">全文</button>
                  <button class="chip" v-if="sourceInfo.punctuated_text" :class="{ active: subView === 'punctuated' }" @click="subView = 'punctuated'">标点整理</button>
                  <button class="btn btn-sm" style="margin-left: auto" @click="copyTranscript">复制全文</button>
                </div>
                <div v-if="subView === 'punctuated' && sourceInfo.punctuated_text" class="transcript-text">{{ sourceInfo.punctuated_text }}</div>
                <div v-else-if="subView === 'full' && sourceInfo && sourceInfo.transcript" class="transcript-text">{{ sourceInfo.transcript }}</div>
                <div v-else-if="subtitleSegments.length" class="sub-lines">
                  <div class="sub-line" v-for="(s, i) in subtitleSegments" :key="i">
                    <span class="sub-time">{{ fmtSeconds(s.start) }}</span>
                    <span class="sub-text">{{ s.text }}</span>
                  </div>
                </div>
                <div v-else-if="sourceInfo && sourceInfo.transcript" class="transcript-text">{{ sourceInfo.transcript }}</div>
              </div>

              <div v-else-if="!isNote && tab === 'board'" class="tab-body">
                <p v-if="current.options && current.options.storyboard === false" class="sub-hint">
                  这条在新建时选择了「不做分镜」，所以没有检测镜头。口播类内容通常不需要逐镜头拆分；
                  需要时可以重新新建一条并勾选「做分镜」。
                </p>
                <p v-else-if="!(current.data.storyboard && current.data.storyboard.length)" class="sub-hint">
                  这条还没有镜头数据。重新转写后会自动做真实切镜检测，生成分镜表。
                </p>
                <template v-else>
                  <p class="sub-hint">镜头由画面切镜检测生成，缩略图是对应关键帧，不是模型编造。</p>
                  <table class="storyboard">
                    <thead><tr><th>时间</th><th>画面</th><th>镜头</th><th>口播</th><th>备注</th></tr></thead>
                    <tbody>
                      <tr v-for="(s, i) in current.data.storyboard" :key="i">
                        <td>{{ s.time }}</td>
                        <td><img v-if="s.keyframe" class="shot-thumb" :src="'/media/shots/' + sourceInfo.id + '/' + s.keyframe" loading="lazy" /></td>
                        <td>{{ s.shot }}<div class="shot-dur">{{ s.duration }}s</div></td>
                        <td>{{ s.line }}</td>
                        <td>{{ s.note }}</td>
                      </tr>
                    </tbody>
                  </table>
                </template>
              </div>
            </article>
          </div>
        </div>

        <div v-else class="account-view">
          <aside class="card account-side">
            <div class="block-head"><span>对标账号</span></div>
            <p class="hint">填视频号昵称（一字不差），自动拉主页资料和作品列表。每次调用按次计费。</p>
            <div class="account-add">
              <input class="input" v-model="accountNickname" placeholder="账号昵称，例如：玖妈懂敏宝" @keyup.enter="previewAccount" />
              <div class="account-add-row">
                <button class="btn btn-primary btn-sm" :disabled="accountBusy" @click="previewAccount">{{ accountBusy ? '查询中…' : '查看基础信息' }}</button>
              </div>
              <p class="hint" style="margin-top:6px">只查主页，不抓作品，约 $0.03。看到作品数、直播、合集后，再决定抓哪个范围。</p>
            </div>

            <div class="spend-line" v-if="spendToday">
              今日已调用 {{ spendToday.calls }} 次 · 约 {{ spendToday.est_usd.toFixed(2) }} 美元
              <span class="spend-note">（本机记账，不含手动脚本）</span>
            </div>

            <div class="account-list">
              <button v-for="a in accounts" :key="a.id"
                      class="queue-item" :class="{ active: accountCurrent && accountCurrent.id === a.id }"
                      @click="selectAccount(a.id)">
                <span class="light done"></span>
                <span>
                  <span class="queue-title">{{ a.name }}</span>
                  <span class="queue-meta">{{ a.platform }} · {{ a.video_count }} 条 · {{ (a.fetched_at || '').slice(0, 10) }}</span>
                </span>
              </button>
              <div v-if="!accounts.length" class="empty-state" style="padding: 20px 8px">
                <p>还没有账号。填昵称加一个。</p>
              </div>
            </div>

            <details class="account-batch">
              <summary>批量粘贴视频链接（备用）</summary>
              <p class="hint">视频号以外的平台，或接口不可用时用这个。</p>
              <textarea class="input account-links" v-model="accountForm.links" rows="4" placeholder="https://..."></textarea>
              <div class="account-actions">
                <button class="btn btn-sm" :disabled="accountSubmitting" @click="submitAccount">提交链接</button>
              </div>
            </details>
          </aside>

          <div class="account-main">
            <div v-if="!accountCurrent" class="card empty-state">
              <div class="ico">◫</div>
              <h2>选一个账号，或添加新账号</h2>
              <p>左边填视频号昵称，系统会拉回主页资料和作品列表，并按互动排序。</p>
            </div>

            <template v-else>
              <article class="card account-cover">
                <img v-if="accountCurrent.avatar" class="account-avatar" :src="accountCurrent.avatar" alt="" referrerpolicy="no-referrer" />
                <div class="account-cover-main">
                  <h2>
                    {{ accountCurrent.name }}
                    <span v-if="accountVerify" class="verify-badge">{{ accountVerify }}</span>
                  </h2>
                  <p class="account-bio">{{ accountCurrent.bio || '没有简介' }}</p>
                  <div class="account-meta">
                    {{ accountCurrent.platform }}
                    <template v-if="accountRegion"> · {{ accountRegion }}</template>
                    · {{ accountCurrent.username.slice(0, 22) }}… · 抓取于 {{ (accountCurrent.fetched_at || '').slice(0, 16).replace('T', ' ') }}
                  </div>
                </div>
                <div class="account-cover-actions">
                  <button class="btn btn-sm" :disabled="accountBusy" @click="refreshAccount">刷新</button>
                  <button class="btn btn-sm btn-primary" :disabled="accountBusy || !accountCurrent.videos.length" @click="analyzeAccount">生成账号分析</button>
                </div>
              </article>

              <p class="hint" :class="{ 'msg-bad': accountMessageBad }" v-if="accountMessage">{{ accountMessage }}</p>

              <article class="card account-base">
                <div class="block-head">
                  <span>基础信息</span>
                  <span class="mono">采集范围：{{ accountMetrics.range || '未采集' }} · 已存 {{ (accountCurrent.videos || []).length }} 条</span>
                </div>
                <div class="base-grid">
                  <div><span class="base-k">作品总数</span><span class="base-v">{{ accountMetrics.posts || '—' }}</span></div>
                  <div><span class="base-k">累计直播</span><span class="base-v">{{ accountMetrics.live_hours || 0 }} 小时</span></div>
                  <div><span class="base-k">合集</span><span class="base-v">{{ accountMetrics.collections || 0 }} 个</span></div>
                  <div><span class="base-k">地区</span><span class="base-v">{{ accountMetrics.region || '—' }}</span></div>
                  <div><span class="base-k">原创标识</span><span class="base-v">{{ accountMetrics.original_flag ? '有' : '无' }}</span></div>
                  <div><span class="base-k">关联公众号</span><span class="base-v">{{ linkedText }}</span></div>
                </div>
                <p class="hint" style="margin:8px 0 0">粉丝数、播放量、账号总互动：视频号不公开，无法获取。</p>
                <div class="collect-row">
                  <span class="qualify-label">采集范围</span>
                  <button v-for="o in rangeOptions" :key="o.key" class="chip"
                          :class="{ active: collectRange === o.key }" @click="collectRange = o.key">{{ o.label }}</button>
                  <span class="range-est" v-if="rangeEstimate()">预计 {{ rangeEstimate().items }} 条 · 约 {{ rangeEstimate().usd }} 美元</span>
                  <button class="btn btn-primary btn-sm" :disabled="accountBusy" @click="startCollect">{{ accountBusy ? '抓取中…' : '开始抓取' }}</button>
                </div>
              </article>

              <div class="account-stats">
                <div class="stat"><span class="stat-num">{{ accountStats.count }}</span><span class="stat-label">作品数</span></div>
                <div class="stat"><span class="stat-num">{{ accountStats.median }}</span><span class="stat-label">互动中位数</span></div>
                <div class="stat"><span class="stat-num">{{ accountStats.top }}</span><span class="stat-label">最高互动</span></div>
                <div class="stat"><span class="stat-num small">{{ accountStats.from || '—' }}</span><span class="stat-label">最早</span></div>
                <div class="stat"><span class="stat-num small">{{ accountStats.to || '—' }}</span><span class="stat-label">最新</span></div>
              </div>

              <article class="card account-analysis" v-if="accountAnalysis">
                <div class="block-head">
                  <span>账号分析</span>
                  <span class="mono" v-if="accountAnalysis.evidence">
                    依据 {{ accountAnalysis.evidence.analyzed }} 条 / 共 {{ accountAnalysis.evidence.total_posts }} 条
                  </span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.business_type">
                  <span class="analysis-label">账号类型</span><span>{{ accountAnalysis.business_type }}</span>
                </div>
                <div class="analysis-row"><span class="analysis-label">定位</span><span>{{ accountAnalysis.positioning }}</span></div>
                <div class="analysis-row" v-if="accountAnalysis.audience"><span class="analysis-label">受众</span><span>{{ accountAnalysis.audience }}</span></div>
                <div class="analysis-row" v-if="accountAnalysis.style"><span class="analysis-label">风格</span><span>{{ accountAnalysis.style }}</span></div>
                <div class="analysis-row" v-if="accountAnalysis.tags && accountAnalysis.tags.length">
                  <span class="analysis-label">标签</span>
                  <span class="tag-row"><span class="tag green" v-for="t in accountAnalysis.tags" :key="t">{{ t }}</span></span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.topics && accountAnalysis.topics.length">
                  <span class="analysis-label">选题</span>
                  <span>
                    <span class="topic-line" v-for="(t, i) in accountAnalysis.topics" :key="i">
                      {{ t.topic }}<span class="analysis-muted" v-if="t.share">（{{ t.share }}）</span>
                    </span>
                  </span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.cadence">
                  <span class="analysis-label">更新</span>
                  <span>{{ accountAnalysis.cadence.frequency }}<template v-if="accountAnalysis.cadence.notes"> · {{ accountAnalysis.cadence.notes }}</template></span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.top_posts && accountAnalysis.top_posts.length">
                  <span class="analysis-label">账号内高互动</span>
                  <span>
                    <span class="topic-line" v-for="(p, i) in accountAnalysis.top_posts" :key="i">
                      {{ p.title }}<span class="analysis-muted" v-if="p.why"> — {{ p.why }}</span>
                    </span>
                  </span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.replicable && accountAnalysis.replicable.length">
                  <span class="analysis-label">可复制</span>
                  <span><span class="topic-line" v-for="(t, i) in accountAnalysis.replicable" :key="i">{{ t }}</span></span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.spread">
                  <span class="analysis-label">传播</span><span>{{ accountAnalysis.spread }}</span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.top_patterns && accountAnalysis.top_patterns.length">
                  <span class="analysis-label">爆款共性</span>
                  <span><span class="topic-line" v-for="(t, i) in accountAnalysis.top_patterns" :key="i">{{ t }}</span></span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.not_replicable && accountAnalysis.not_replicable.length">
                  <span class="analysis-label">不宜照搬</span>
                  <span><span class="topic-line" v-for="(t, i) in accountAnalysis.not_replicable" :key="i">{{ t }}</span></span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.risks && accountAnalysis.risks.length">
                  <span class="analysis-label">注意</span>
                  <span><span class="topic-line" v-for="(t, i) in accountAnalysis.risks" :key="i">{{ t }}</span></span>
                </div>
                <div class="analysis-row" v-if="accountAnalysis.unknowns && accountAnalysis.unknowns.length">
                  <span class="analysis-label">数据不足</span>
                  <span><span class="topic-line" v-for="(t, i) in accountAnalysis.unknowns" :key="i">{{ t }}</span></span>
                </div>
                <p class="hint" v-if="accountAnalysis.evidence" style="margin-top:10px">
                  分析方式：{{ accountAnalysis.evidence.method }}；时间范围 {{ accountAnalysis.evidence.from }} ~ {{ accountAnalysis.evidence.to }}。
                  粉丝数、播放量平台不公开，未做估算。
                </p>
              </article>

              <article class="card account-videos">
                <div class="block-head">
                  <span>作品列表</span>
                  <span class="mono">共抓取 {{ (accountCurrent.videos || []).length }} 条</span>
                </div>
                <p class="hint">双榜只展示要用的候选：历史爆款看它验证过的结构，近期榜看它现在在打什么。
                  互动 = 点赞 + 评论 + 转发 + 收藏；播放量平台不公开，这里只做账号内相对排名。</p>
                <div class="qualify-row">
                  <button class="chip" :class="{ active: videoView === 'boards' }" @click="videoView = 'boards'">双榜</button>
                  <button class="chip" :class="{ active: videoView === 'all' }" @click="videoView = 'all'">全部作品（{{ (accountCurrent.videos || []).length }}）</button>
                  <template v-if="videoView === 'all'">
                    <span class="qualify-label">只看</span>
                    <select class="select qualify-input" v-model="filterMetric" @change="saveFilters">
                      <option value="shares">转发</option>
                      <option value="likes">点赞</option>
                      <option value="comments">评论</option>
                      <option value="favorites">收藏</option>
                      <option value="total">总互动</option>
                    </select>
                    <span>≥</span>
                    <input class="input qualify-input" type="number" min="0" v-model.number="filterMin" @change="saveFilters" />
                  </template>
                </div>

                <template v-if="videoView === 'boards'">
                  <div v-for="board in accountBoards" :key="board.key" class="board-block">
                    <div class="block-head board-head">
                      <span>{{ board.title }}</span>
                      <span class="mono">{{ board.items.length }} 条 · {{ board.note }}</span>
                    </div>
                    <table class="storyboard account-table">
                      <thead><tr><th>互动</th><th>发布时间</th><th>文案</th><th></th></tr></thead>
                      <tbody>
                        <tr v-for="v in board.items" :key="board.key + v.id">
                          <td class="mono">{{ engagement(v) }}<div class="shot-dur">赞{{ v.likes }} 评{{ v.comments }} 转{{ v.shares }} 藏{{ v.favorites }}</div></td>
                          <td class="mono">{{ (v.published_at || '').slice(0, 10) }}</td>
                          <td>{{ v.text }}</td>
                          <td>
                            <span v-if="decomposedByVideo[v.id]" class="done-tag">{{ decomposedByVideo[v.id].status === 'done' ? '已拆解' : '处理中' }}</span>
                            <button class="btn btn-sm" :disabled="videoBusyId === v.id || accountVideoAction(v).kind === 'busy'"
                                    @click="decomposeAccountVideo(v)">{{ videoBusyId === v.id ? '处理中…' : accountVideoAction(v).text }}</button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <p v-if="!board.items.length" class="hint">未检测到置顶作品（该账号主页没有置顶，或接口未返回）。</p>
                  </div>
                  <p v-if="!accountBoards.length" class="hint">还没有可展示的作品，先点上面的「刷新」抓一次。</p>
                </template>

                <table v-else class="storyboard account-table">
                  <thead><tr><th>互动</th><th>发布时间</th><th>文案</th><th></th></tr></thead>
                  <tbody>
                    <tr v-for="v in accountVideosRanked" :key="v.id">
                      <td class="mono">{{ engagement(v) }}<div class="shot-dur">赞{{ v.likes }} 评{{ v.comments }} 转{{ v.shares }} 藏{{ v.favorites }}</div></td>
                      <td class="mono">{{ (v.published_at || '').slice(0, 10) }}</td>
                      <td>{{ v.text }}</td>
                      <td>
                            <span v-if="decomposedByVideo[v.id]" class="done-tag">{{ decomposedByVideo[v.id].status === 'done' ? '已拆解' : '处理中' }}</span>
                            <button class="btn btn-sm" :disabled="videoBusyId === v.id || accountVideoAction(v).kind === 'busy'"
                                    @click="decomposeAccountVideo(v)">{{ videoBusyId === v.id ? '处理中…' : accountVideoAction(v).text }}</button>
                          </td>
                    </tr>
                  </tbody>
                </table>
              </article>
            </template>
          </div>
        </div>
      </section>

      <!-- 数据库 -->
      <section v-else-if="route === 'database'" class="page" :key="route">
        <header class="page-head">
          <div>
            <h1>数据库</h1>
            <p>数据复盘、账号数据、内容数据和素材存档都在这里。</p>
          </div>
          <div class="head-actions">
            <button class="btn" @click="refresh">刷新</button>
            <button class="btn btn-primary" @click="openNew">导入素材</button>
          </div>
        </header>

        <div class="db-tabs">
          <button class="db-tab" :class="{ active: dbTab === 'review' }" @click="setDbTab('review')">数据复盘</button>
          <button class="db-tab" :class="{ active: dbTab === 'account' }" @click="setDbTab('account')">账号数据</button>
          <button class="db-tab" :class="{ active: dbTab === 'content' }" @click="setDbTab('content')">内容数据</button>
          <button class="db-tab" :class="{ active: dbTab === 'assets' }" @click="setDbTab('assets')">素材存档</button>
        </div>

        <div v-if="dbTab === 'review'" class="card db-empty">
          <div class="ico" style="margin: 0 auto 14px; width: 52px; height: 52px; border-radius: 16px; background: var(--green-soft); display: grid; place-items: center; font-size: 20px;">▤</div>
          <h3>数据复盘还没开始</h3>
          <p>发布后记录 T+1、T+3、T+7 的数据，和拆解时的预测做对照。等自动抓取接入后，这里会有真实数据。</p>
        </div>

        <div v-else-if="dbTab === 'account'" class="card" style="padding: 10px 16px 16px">
          <table class="data-table">
            <thead>
              <tr><th>日期</th><th>粉丝总数</th><th>净增</th><th>新增</th><th>取关</th><th>总阅读</th><th>单条最高</th><th>互动率</th><th>同步时间</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in metricsList" :key="m.stat_date">
                <td class="mono">{{ m.stat_date }}</td>
                <td class="strong mono">{{ fmtNum(m.followers_total) }}</td>
                <td class="mono" :style="{ color: m.followers_net > 0 ? 'var(--green-deep)' : (m.followers_net < 0 ? 'var(--warn)' : 'var(--muted)') }">{{ m.followers_net > 0 ? '+' : '' }}{{ m.followers_net }}</td>
                <td class="mono">{{ m.followers_add }}</td>
                <td class="mono">{{ m.followers_del }}</td>
                <td class="strong mono">{{ fmtNum(m.play_total) }}</td>
                <td class="mono">{{ fmtNum(m.top_play) }}<span class="sub" v-if="m.top_title">{{ m.top_title.slice(0, 18) }}</span></td>
                <td class="mono">{{ Number(m.engagement_rate || 0).toFixed(2) }}%</td>
                <td class="mono">{{ fmtDateTime(m.synced_at) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!metricsList.length" class="empty-state">
            <h2>还没有同步记录</h2>
            <p>在首页点「同步数据」，或等每日自动同步跑完。</p>
          </div>
        </div>

        <div v-else-if="dbTab === 'content'" class="card db-empty">
          <h3>内容数据还没开始</h3>
          <p>每条作品的播放、点赞、评论、转发、涨粉，会在这里逐条对照。</p>
        </div>

        <div v-else class="card" style="padding: 10px 16px 16px">
          <table class="data-table">
            <thead><tr><th>时间</th><th>标题</th><th>平台</th><th>作者</th><th>状态</th><th>钩子</th></tr></thead>
            <tbody>
              <tr v-for="it in items" :key="it.id" @click="go('deconstruct'); selectItem(it.id)">
                <td class="mono">{{ fmtDateTime(it.created_at) }}</td>
                <td><span class="strong">{{ it.title }}</span><span class="sub" v-if="it.summary">{{ it.summary.slice(0, 42) }}</span></td>
                <td>{{ it.platform || '—' }}</td>
                <td>{{ it.author || '—' }}</td>
                <td><span class="light" :class="it.status" style="display:inline-block;margin-right:6px"></span>{{ statusText(it.status) }}</td>
                <td class="mono">{{ it.hook_score || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!items.length" class="empty-state">
            <h2>还没有素材</h2>
            <p>导入第一条视频后，这里会自动留档。</p>
            <button class="btn btn-primary" @click="openNew">导入素材</button>
          </div>
        </div>
      </section>

      <!-- 设置 -->
      <section v-else-if="route === 'settings'" class="page" :key="route">
        <header class="page-head">
          <div>
            <h1>设置</h1>
            <p>运行模式、模型接入与数据位置。所有配置只保存在本机。</p>
          </div>
        </header>

        <div class="settings-grid">
          <section class="card setting-card">
            <h3>运行模式</h3>
            <div class="desc">首页数据、转写与拆解均来自真实来源；演示内容会单独标注。</div>
            <div class="setting-row">
              <div>
                <div class="setting-name">数据模式</div>
                <div class="setting-note">视频号后台同步 + 本地转写 + 云端模型</div>
              </div>
              <div class="setting-value"><span class="badge-on">真实数据</span></div>
            </div>
            <div class="setting-row">
              <div>
                <div class="setting-name">视频号自动同步</div>
                <div class="setting-note">每天 {{ (settings && settings.sync && settings.sync.time) || '08:30' }} 同步前一天数据 · 今日尝试 {{ (settings && settings.sync && settings.sync.attempts) || 0 }}/3 次</div>
                <div class="setting-note" v-if="settings && settings.sync && settings.sync.last_at">上次：{{ settings.sync.last_at.replace('T', ' ').slice(0, 16) }} · {{ settings.sync.last_status === 'ok' ? '成功' : (settings.sync.last_status === 'login_expired' ? '登录已失效，请重新扫码' : (settings.sync.last_status === 'login_renewed' ? '已重新扫码，等待同步' : '失败')) }}</div>
              </div>
              <div class="setting-value">
                <button class="btn btn-sm warn" v-if="settings && settings.sync && settings.sync.last_status === 'login_expired'" :disabled="scanning" @click="startScan">{{ scanning ? '等待扫码…' : '重新扫码' }}</button>
              </div>
            </div>
            <div class="setting-row">
              <div><div class="setting-name">项目与数据目录</div><div class="setting-note">整个文件夹复制即可备份</div></div>
              <div class="setting-value">{{ settings && settings.data_dir }}</div>
            </div>
          </section>

          <section class="card setting-card">
            <h3>模型接入</h3>
            <div class="desc">本地转写 + 云端拆解；字幕会发送给云端服务商，视频文件不会。写稿模型后续接入。</div>
            <div class="setting-row">
              <div>
                <div class="setting-name">本地转写</div>
                <div class="setting-note">faster-whisper · {{ (settings && settings.asr && settings.asr.device === 'cuda') ? '显卡加速' : 'CPU（显卡未启用）' }} · <span v-if="settings && settings.asr && settings.asr.loaded">模型已加载</span><span v-else>按需加载</span></div>
              </div>
              <div class="setting-value">
                <select class="input" style="width: 150px; height: 34px" v-model="asrModel" @change="saveAsrModel">
                  <option value="small">small · 快</option>
                  <option value="medium">medium · 准</option>
                </select>
              </div>
            </div>
            <div class="setting-row">
              <div>
                <div class="setting-name">云端拆解模型</div>
                <div class="setting-note">OpenAI 兼容接口 · 推荐 DeepSeek · 按量计费</div>
              </div>
              <div class="setting-value">
                <span class="badge-on" v-if="llmTest === 'ok'">连接正常</span>
                <span class="badge-soon" v-else-if="llmTest === 'fail'">连接失败</span>
                <span class="badge-soon" v-else>{{ (settings && settings.llm && settings.llm.key_set) ? 'Key 已保存' : '未配置' }}</span>
              </div>
            </div>
            <div class="llm-form">
              <div class="llm-field">
                <label class="label">API 地址</label>
                <input class="input" v-model="llmForm.base_url" placeholder="https://api.deepseek.com" />
              </div>
              <div class="llm-field">
                <label class="label">模型</label>
                <input class="input" v-model="llmForm.model" placeholder="deepseek-flash" />
              </div>
              <div class="llm-field">
                <label class="label">API Key</label>
                <input class="input" type="password" v-model="llmForm.api_key" :placeholder="(settings && settings.llm && settings.llm.key_set) ? '已保存，留空则不修改' : 'sk-...'" />
              </div>
              <div class="llm-actions">
                <button class="btn btn-sm btn-primary" :disabled="savingLlm" @click="saveLlm">{{ savingLlm ? '保存中…' : '保存' }}</button>
                <button class="btn btn-sm" :disabled="testingLlm" @click="testLlm">{{ testingLlm ? '测试中…' : '测试连接' }}</button>
                <span class="llm-msg" :class="{ bad: llmMessageBad }" v-if="llmMessage">{{ llmMessage }}</span>
              </div>
            </div>
            <div class="setting-row">
              <div>
                <div class="setting-name">画面字幕 OCR</div>
                <div class="setting-note">智谱视觉模型 · 只上传字幕区域 · 用于校正转写错字</div>
              </div>
              <div class="setting-value">
                <span class="badge-on" v-if="ocrTest === 'ok'">连接正常</span>
                <span class="badge-soon" v-else-if="ocrTest === 'fail'">连接失败</span>
                <span class="badge-soon" v-else>{{ (settings && settings.ocr && settings.ocr.key_set) ? 'Key 已保存' : '未配置' }}</span>
              </div>
            </div>
            <div class="llm-form">
              <div class="llm-field">
                <label class="label">API 地址</label>
                <input class="input" v-model="ocrForm.base_url" placeholder="https://open.bigmodel.cn/api/paas/v4" />
              </div>
              <div class="llm-field">
                <label class="label">模型</label>
                <input class="input" v-model="ocrForm.model" placeholder="glm-4.6v-flash" />
              </div>
              <div class="llm-field">
                <label class="label">API Key</label>
                <input class="input" type="password" v-model="ocrForm.api_key" :placeholder="(settings && settings.ocr && settings.ocr.key_set) ? '已保存，留空则不修改' : '智谱 API Key'" />
              </div>
              <div class="llm-actions">
                <button class="btn btn-sm btn-primary" :disabled="savingOcr" @click="saveOcr">{{ savingOcr ? '保存中…' : '保存' }}</button>
                <button class="btn btn-sm" :disabled="testingOcr" @click="testOcr">{{ testingOcr ? '测试中…' : '测试连接' }}</button>
                <span class="llm-msg" :class="{ bad: ocrMessageBad }" v-if="ocrMessage">{{ ocrMessage }}</span>
              </div>
            </div>
            <div class="setting-row">
              <div><div class="setting-name">写稿模型</div><div class="setting-note">DeepSeek API · 按量计费</div></div>
              <div class="setting-value"><span class="badge-soon">待接入</span></div>
            </div>
          </section>

          <section class="card setting-card">
            <h3>数据接口（账号分析）</h3>
            <div class="desc">视频号公开网页不提供作品列表，账号级分析走第三方接口。Key 只存本机，页面不回显；按次计费，约 $0.01/次。</div>
            <div class="setting-row">
              <div>
                <div class="setting-name">TikHub API</div>
                <div class="setting-note">短号转内部号 + 主页资料 + 作品列表</div>
              </div>
              <div class="setting-value">
                <span class="badge-on" v-if="tikhubMsg && !tikhubMsgBad">已跑通</span>
                <span class="badge-soon" v-else>{{ (settings && settings.tikhub && settings.tikhub.key_set) ? 'Key 已保存' : '未配置' }}</span>
              </div>
            </div>
            <div class="llm-form">
              <div class="llm-field">
                <label class="label">API Key</label>
                <input class="input" type="password" v-model="tikhubForm.api_key" :placeholder="(settings && settings.tikhub && settings.tikhub.key_set) ? '已保存，留空则不修改' : '粘贴 TikHub API Key'" />
              </div>
              <div class="llm-actions">
                <button class="btn btn-sm btn-primary" :disabled="savingTikhub" @click="saveTikhub">{{ savingTikhub ? '保存中…' : '保存' }}</button>
              </div>
            </div>
            <div class="llm-form" style="margin-top: 12px">
              <div class="llm-field">
                <label class="label">测试：视频号 ID</label>
                <input class="input" v-model="tikhubId" placeholder="sph..." />
              </div>
              <div class="llm-actions">
                <button class="btn btn-sm" :disabled="testingTikhub" @click="testTikhub">{{ testingTikhub ? '调用中…' : '拉取账号资料与作品' }}</button>
                <span class="llm-msg" :class="{ bad: tikhubMsgBad }" v-if="tikhubMsg">{{ tikhubMsg }}</span>
              </div>
            </div>

            <div class="setting-row" style="margin-top: 18px; border-top: 1px solid var(--line-soft); padding-top: 14px">
              <div>
                <div class="setting-name">DataXAPI（备用渠道）</div>
                <div class="setting-note">按昵称搜账号 → 内部 ID → 主页 → 作品列表；新号有免费试用</div>
              </div>
              <div class="setting-value">
                <span class="badge-on" v-if="dataxMsg && !dataxMsgBad">已跑通</span>
                <span class="badge-soon" v-else>{{ (settings && settings.dataxapi && settings.dataxapi.key_set) ? 'Key 已保存' : '未配置' }}</span>
              </div>
            </div>
            <div class="llm-form">
              <div class="llm-field">
                <label class="label">API Key</label>
                <input class="input" type="password" v-model="dataxForm.api_key" :placeholder="(settings && settings.dataxapi && settings.dataxapi.key_set) ? '已保存，留空则不修改' : '粘贴 DataXAPI Key'" />
              </div>
              <div class="llm-actions">
                <button class="btn btn-sm btn-primary" :disabled="savingDatax" @click="saveDatax">{{ savingDatax ? '保存中…' : '保存' }}</button>
              </div>
            </div>
            <div class="llm-form" style="margin-top: 12px">
              <div class="llm-field">
                <label class="label">测试：账号昵称（一字不差）</label>
                <input class="input" v-model="dataxNickname" placeholder="例如：玖妈懂敏宝" />
              </div>
              <div class="llm-actions">
                <button class="btn btn-sm" :disabled="testingDatax" @click="testDatax">{{ testingDatax ? '调用中…' : '搜账号并拉作品' }}</button>
                <span class="llm-msg" :class="{ bad: dataxMsgBad }" v-if="dataxMsg">{{ dataxMsg }}</span>
              </div>
            </div>
          </section>

          <section class="card setting-card">
            <h3>数据与备份</h3>
            <div class="desc">数据库、上传文件与导出文件都在项目内的 data 目录。</div>
            <div class="setting-row">
              <div><div class="setting-name">数据库</div><div class="setting-note">app.db · SQLite</div></div>
              <div class="setting-value"><span class="badge-on">正常</span></div>
            </div>
            <div class="setting-row">
              <div><div class="setting-name">上传文件</div><div class="setting-note">data/uploads · 单文件上限 500MB</div></div>
              <div class="setting-value"><span class="badge-on">正常</span></div>
            </div>
          </section>

          <section class="card setting-card">
            <h3>关于</h3>
            <div class="desc">本地优先，数据不出本机。</div>
            <div class="setting-row">
              <div><div class="setting-name">版本</div><div class="setting-note">本地运行</div></div>
              <div class="setting-value">v{{ (settings && settings.version) || '0.12.0' }}</div>
            </div>
            <div class="setting-row">
              <div><div class="setting-name">服务地址</div><div class="setting-note">仅监听回环地址</div></div>
              <div class="setting-value">127.0.0.1:8741</div>
            </div>
          </section>
        </div>
      </section>

      <!-- 改写 -->
      <section v-else-if="route === 'rewrite'" class="page" :key="route">
        <header class="page-head">
          <div>
            <h1>改写</h1>
            <p>基于一条拆解的结构，另写一份我们自己的口播稿。拆解只读，原话不会被改动。</p>
          </div>
          <div class="head-actions">
            <button class="btn" @click="refresh">刷新</button>
            <button class="btn" @click="go('deconstruct')">去对标拆解</button>
          </div>
        </header>

        <div class="deco-layout">
          <aside class="card queue">
            <div class="queue-list">
              <button v-for="it in rewriteItems" :key="it.id"
                      class="queue-item" :class="{ active: current && current.id === it.id }"
                      @click="openRewriteItem(it.id)">
                <span class="queue-time">{{ clock(it.created_at) }}</span>
                <span class="light" :class="it.status"></span>
                <span>
                  <span class="queue-title">{{ it.title }}</span>
                  <span class="queue-meta">{{ it.platform || '—' }} · {{ it.has_rewrite ? '已有改写稿' : '未改写' }}</span>
                </span>
              </button>
              <div v-if="!rewriteItems.length" class="empty-state">
                <p>还没有已完成的拆解。先去「对标拆解」拆一条。</p>
              </div>
            </div>
          </aside>

          <div class="detail">
            <div v-if="!current || current.status !== 'done'" class="card empty-state">
              <div class="ico">✎</div>
              <h2>选一条拆解开始改写</h2>
              <p>左边是已完成的对标拆解。改写只读它的结构，不会改动原始字幕和拆解结果。</p>
              <button class="btn" @click="go('deconstruct')">去对标拆解</button>
            </div>

            <article v-else class="card scene">
              <header class="scene-head">
                <div>
                  <div class="scene-kicker">改写 · 基于对标「{{ current.title }}」</div>
                  <h2 class="scene-title">{{ current.title }}</h2>
                  <div class="scene-meta">
                    <span v-if="structureOutline.length">结构 {{ structureOutline.length }} 段</span>
                    <span v-if="rewriteData && rewriteData.generated_at">生成于 {{ fmtDateTime(rewriteData.generated_at) }}</span>
                    <span v-if="current.data && current.data.author">原作者 {{ current.data.author }}</span>
                  </div>
                </div>
                <div class="scene-actions">
                  <button class="btn btn-sm btn-primary" :disabled="rewriteLoading" @click="generateRewrite">
                    {{ rewriteLoading ? '生成中…' : (rewriteData ? '重新生成' : '生成改写稿') }}
                  </button>
                </div>
              </header>

              <div class="rewrite-grid">
                <div class="rewrite-structure">
                  <div class="block-head"><span>结构骨架（来自拆解，只读）</span></div>
                  <ol class="outline">
                    <li v-for="(s, i) in structureOutline" :key="i">
                      <span class="outline-time">{{ s.start }}–{{ s.end }}</span>
                      <span class="outline-role">{{ s.role }}</span>
                      <span class="outline-gist">{{ s.gist }}</span>
                    </li>
                  </ol>
                  <p class="hint">改写规则（语气、人称、IP 定位）要等 IP 档案定稿后再接进来；当前是按结构复述的参考稿。</p>
                </div>

                <div class="rewrite-body">
                  <p v-if="rewriteError" class="sub-hint">{{ rewriteError }}</p>
                  <p v-if="!rewriteData" class="sub-hint">还没有改写稿。点右上角「生成改写稿」，会按左边这套结构重写一版。</p>
                  <template v-else>
                    <div class="view-toggle">
                      <button class="chip" :class="{ active: rewriteView === 'parts' }" @click="rewriteView = 'parts'">分段</button>
                      <button class="chip" :class="{ active: rewriteView === 'full' }" @click="rewriteView = 'full'">全文</button>
                      <button class="btn btn-sm" style="margin-left:auto" @click="copyScript">复制全文</button>
                    </div>
                    <div v-if="rewriteView === 'full'" class="script-text">{{ fullScriptText }}</div>
                    <template v-else>
                      <div class="script-block" v-for="(sec, i) in scriptSections" :key="i">
                        <div class="script-label">{{ sec.role }}</div>
                        <div class="script-text">{{ sec.text }}</div>
                      </div>
                    </template>
                    <p class="hint">这里是我们重写的稿子，不是原视频原话。原话请看「对标拆解 → 原始字幕」。</p>
                  </template>
                </div>
              </div>
            </article>
          </div>
        </div>
      </section>

      <!-- 规划中 -->
      <section v-else class="page" :key="route">
        <header class="page-head">
          <div>
            <h1>{{ placeholder.title }}</h1>
            <p>{{ placeholder.desc }}</p>
          </div>
        </header>
        <div class="card empty-state">
          <div class="ico">{{ placeholder.icon }}</div>
          <p>{{ placeholder.note }}</p>
          <button class="btn" @click="go('home')">回到首页</button>
        </div>
      </section>
    </div>
  </main>

  <!-- 新建拆解 -->
  <div v-if="modalOpen" class="modal-backdrop" @click.self="closeNew">
    <div class="modal">
      <div class="modal-head">
        <div>
          <div class="modal-title">新建拆解</div>
          <div class="modal-sub">上传视频/音频，或直接粘贴视频号、抖音、小红书链接，系统会自动解析下载。</div>
        </div>
        <button class="modal-close" @click="closeNew">×</button>
      </div>

      <div class="dropzone" :class="{ drag: dragging }"
           @click="$refs.fileInput.click()"
           @dragover.prevent="dragging = true"
           @dragleave.prevent="dragging = false"
           @drop.prevent="onDrop">
        <strong>{{ file ? file.name : '拖入视频，或点击选择文件' }}</strong>
        <span v-if="!file">支持 mp4 / mov / m4v，单文件不超过 500MB</span>
        <span v-else>{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span>
      </div>
      <input ref="fileInput" type="file" accept="video/*,audio/*" style="display:none" @change="onFile" />

      <div class="form-grid">
        <div class="field"><label class="label">标题</label><input class="input" v-model="form.title" placeholder="不填则使用文件名" /></div>
        <div class="field"><label class="label">作者</label><input class="input" v-model="form.author" placeholder="选填" /></div>
        <div class="field">
          <label class="label">平台</label>
          <select class="select" v-model="form.platform"><option>视频号</option><option>抖音</option><option>小红书</option><option>其他</option></select>
        </div>
        <div class="field"><label class="label">链接</label><input class="input" v-model="form.url" placeholder="https://…（选填）" /></div>
      </div>

      <label class="switch-row">
        <input type="checkbox" v-model="form.storyboard" class="switch-box" />
        <span>
          <span class="switch-title">做分镜（逐镜头拆画面）</span>
          <span class="switch-note">场景、剧情、探店类勾选；单人面对镜头的口播类可以取消，省 40 秒左右。</span>
        </span>
      </label>

      <div class="modal-actions">
        <button class="btn" @click="closeNew">取消</button>
        <button class="btn btn-primary" :disabled="submitting" @click="submitNew">{{ submitting ? '处理中…' : '开始拆解' }}</button>
      </div>
    </div>
  </div>

  <!-- 命令面板 -->
  <div v-if="paletteOpen" class="palette-backdrop" @click.self="closePalette">
    <div class="palette">
      <input ref="paletteInput" class="palette-input" v-model="paletteQuery" placeholder="搜索页面或操作"
             @keydown.down.prevent="paletteMove(1)" @keydown.up.prevent="paletteMove(-1)" @keydown.enter.prevent="paletteRun" />
      <div class="palette-list">
        <div v-for="(c, i) in paletteResults" :key="c.label" class="palette-item" :class="{ active: i === paletteIndex }" @click="runCommand(c)">
          <span class="nav-icon" v-html="icons[c.icon]"></span>
          <span>{{ c.label }}</span>
          <span class="k">{{ c.k }}</span>
        </div>
        <div v-if="!paletteResults.length" class="empty-state" style="padding: 20px"><p>没有匹配的命令</p></div>
      </div>
    </div>
  </div>

  <!-- 手动提供作品链接 -->
  <div v-if="linkPrompt.open" class="modal-backdrop" @click.self="closeLinkPrompt">
    <div class="modal">
      <div class="modal-head">
        <div>
          <div class="modal-title">手动提供这条作品的链接</div>
          <div class="modal-sub">{{ linkPrompt.video && linkPrompt.video.text }}</div>
        </div>
        <button class="modal-close" @click="closeLinkPrompt">×</button>
      </div>
      <p class="hint">
        自动取分享链接需要付费额度。现在可以在微信里打开这条作品 → 分享 → 复制链接，
        粘到下面，下载、转写、拆解都会自动完成。
      </p>
      <textarea class="input account-links" v-model="linkPrompt.text" rows="3"
                placeholder="https://weixin.qq.com/sph/..."></textarea>
      <div class="modal-actions">
        <button class="btn" @click="closeLinkPrompt">取消</button>
        <button class="btn btn-primary" :disabled="linkPrompt.busy" @click="submitVideoLink">{{ linkPrompt.busy ? '提交中…' : '开始拆解' }}</button>
      </div>
    </div>
  </div>

  <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
</div>
`,
  });

  app.mount("#app");
})();
