from pathlib import Path
from html import escape, unescape
import os
import re
import shutil
import markdown
import yaml

DATA_DIR = Path("data/entries")

ENTRY_TEMPLATE_FILE = Path("templates/entry.html")
INDEX_TEMPLATE_FILE = Path("templates/index.html")
CATEGORY_TEMPLATE_FILE = Path("templates/category.html")
TIMELINE_TEMPLATE_FILE = Path("templates/timeline.html")
ARCHIVE_TEMPLATE_FILE = Path("templates/archive.html")
TAGS_TEMPLATE_FILE = Path("templates/tags.html")
STATIC_DIR = Path("static")

SITE_DIR = Path("site")
RICH_PAGES_DIR = Path("rich-pages")
SPECIAL_OUTPUT_DIR = SITE_DIR / "special"
ENTRY_OUTPUT_DIR = SITE_DIR / "entries"
STATIC_OUTPUT_DIR = SITE_DIR / "static"

def make_relative_url(from_directory, target):
    """计算两个本地路径之间的网页相对路径。"""
    relative_path = os.path.relpath(
        target,
        start=from_directory
    )

    return relative_path.replace("\\", "/")


def inject_rich_navigation(output_folder, topic_title):
    """给一个丰富专题中的所有 HTML 页面加入统一导航。"""

    topic_home_file = output_folder / "index.html"
    has_topic_home = topic_home_file.exists()
    archive_home_file = SITE_DIR / "index.html"
    navigation_css_file = STATIC_OUTPUT_DIR / "rich-nav.css"

    for html_file in output_folder.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")

        # 防止同一个页面被重复注入导航
        if 'data-personal-archive-nav="true"' in text:
            continue

        home_href = make_relative_url(
            html_file.parent,
            archive_home_file
        )

        css_href = make_relative_url(
            html_file.parent,
            navigation_css_file
        )

        # 给专题页面连接公共导航样式
        stylesheet_tag = (
            f'<link rel="stylesheet" '
            f'href="{css_href}" '
            f'data-personal-archive-style="true">'
        )

        if 'data-personal-archive-style="true"' not in text:
            head_end_match = re.search(
                r"</head\s*>",
                text,
                flags=re.IGNORECASE
            )

            if head_end_match:
                insert_position = head_end_match.start()

                text = (
                    text[:insert_position]
                    + f"    {stylesheet_tag}\n"
                    + text[insert_position:]
                )
            else:
                print(f"警告：专题页面没有 </head>：{html_file}")

        if has_topic_home:
            page_title = topic_title

            is_topic_home = (
                html_file.resolve() == topic_home_file.resolve()
            )

            if is_topic_home:
                topic_action = """
<span class="pa-topic-nav__current">
    专题首页
</span>
"""
            else:
                topic_home_href = make_relative_url(
                    html_file.parent,
                    topic_home_file
                )

                topic_action = f"""
<a class="pa-topic-nav__link"
   href="{topic_home_href}">
    返回专题首页
</a>
"""
        else:
            # 专题目录没有统一首页：从页面自身 <title> 取标题，仅保留返回个人档案
            page_title = topic_title
            title_match = re.search(
                r"<title[^>]*>(.*?)</title>",
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

            if title_match:
                page_title = unescape(title_match.group(1).strip())

            topic_action = ""

        navigation_html = f"""
<nav class="pa-topic-nav"
     data-personal-archive-nav="true"
     aria-label="专题导航">

    <a class="pa-topic-nav__link"
       href="{home_href}">
        ← 返回个人档案
    </a>

    <span class="pa-topic-nav__title">
        {escape(page_title)}
    </span>

    {topic_action}
</nav>
"""

        # 将统一导航放在 body 开始标签之后
        body_match = re.search(
            r"<body\b[^>]*>",
            text,
            flags=re.IGNORECASE
        )

        if body_match:
            insert_position = body_match.end()

            text = (
                text[:insert_position]
                + "\n"
                + navigation_html
                + text[insert_position:]
            )

            html_file.write_text(text, encoding="utf-8")

            print(f"已加入专题导航：{html_file}")
        else:
            print(f"警告：专题页面没有 <body>：{html_file}")


def read_markdown(file_path):
    text = file_path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) < 3:
        return {}, text

    metadata = yaml.safe_load(parts[1]) or {}
    content = parts[2].strip()

    return metadata, content

def make_badges(items, css_class):
    if not items:
        return '<span class="empty-value">无</span>'

    if isinstance(items, str):
        items = [items]

    badges = []

    for item in items:
        badges.append(
            f'<span class="badge {css_class}">{escape(str(item))}</span>'
        )

    return " ".join(badges)

def make_entry_list(entries):
    if not entries:
        return "<p>这个分类目前还没有公开记录。</p>"

    items = []

    for entry in entries:
        item = f"""
<a class="entry-item" href="{entry['url']}">
    <div class="entry-title">{escape(entry['title'])}</div>
    <div class="entry-date">{escape(entry['date'])}</div>
</a>
"""
        items.append(item)

    return "\n".join(items)

def make_archive_content(entries):
    if not entries:
        return "<p>目前还没有公开记录。</p>"

    month_groups = {}

    for entry in entries:
        date = entry.get("date", "")
        month_key = date[:7] if len(date) >= 7 else "未知日期"

        if month_key not in month_groups:
            month_groups[month_key] = []

        month_groups[month_key].append(entry)

    sections = []

    for month_key, month_entries in month_groups.items():
        if month_key != "未知日期" and "-" in month_key:
            year, month = month_key.split("-", 1)
            month_title = f"{year}年{month}月"
        else:
            month_title = "未知日期"

        section = f"""
<section class="archive-month">
    <h2>{escape(month_title)}</h2>
    <div class="entry-list">
        {make_entry_list(month_entries)}
    </div>
</section>
"""
        sections.append(section)

    return "\n".join(sections)

def make_tags_content(entries):
    tag_groups = {}

    for entry in entries:
        entry_tags = entry.get("tags", [])

        if isinstance(entry_tags, str):
            entry_tags = [entry_tags]

        if not entry_tags:
            continue

        for tag in entry_tags:
            tag_name = str(tag)

            if tag_name not in tag_groups:
                tag_groups[tag_name] = []

            tag_groups[tag_name].append(entry)

    if not tag_groups:
        return "<p>目前还没有标签。</p>"

    sections = []

    for tag_name in sorted(tag_groups):
        tag_entries = tag_groups[tag_name]

        section = f"""
<section class="tag-section">
    <h2>
        #{escape(tag_name)}
        <span class="tag-count">{len(tag_entries)} 篇记录</span>
    </h2>

    <div class="entry-list">
        {make_entry_list(tag_entries)}
    </div>
</section>
"""
        sections.append(section)

    return "\n".join(sections)

def build():
    # 删除上一次生成的网站，防止旧的私密页面残留
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)

    ENTRY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        STATIC_DIR,
        STATIC_OUTPUT_DIR,
        dirs_exist_ok=True
    )

    entry_template = ENTRY_TEMPLATE_FILE.read_text(encoding="utf-8")
    index_template = INDEX_TEMPLATE_FILE.read_text(encoding="utf-8")
    category_template = CATEGORY_TEMPLATE_FILE.read_text(encoding="utf-8")
    timeline_template = TIMELINE_TEMPLATE_FILE.read_text(encoding="utf-8")
    archive_template = ARCHIVE_TEMPLATE_FILE.read_text(encoding="utf-8")
    tags_template = TAGS_TEMPLATE_FILE.read_text(encoding="utf-8")

    public_entries = []

    for markdown_file in DATA_DIR.rglob("*.md"):
        metadata, content = read_markdown(markdown_file)

        if metadata.get("visibility") != "public":
            print(f"跳过私密记录：{markdown_file}")
            continue

        title = str(metadata.get("title", "未命名记录"))
        date = str(metadata.get("date", ""))
        output_name = f"{markdown_file.stem}.html"
        page_type = str(metadata.get("page_type", "markdown"))
        custom_page = str(metadata.get("custom_page", "")).strip()
        categories = metadata.get("categories", [])
        tags = metadata.get("tags", [])

        categories_html = make_badges(categories, "category")
        tags_html = make_badges(tags, "tag")

        if page_type == "custom" and custom_page:
            entry_url = custom_page.replace("\\", "/")
            custom_path = Path(entry_url)

            # special/games/... 对应 rich-pages/games/...
            if custom_path.parts and custom_path.parts[0] == "special":
                source_file = RICH_PAGES_DIR.joinpath(
                    *custom_path.parts[1:]
                )
                source_folder = source_file.parent
                output_folder = SITE_DIR / custom_path.parent

                if source_file.exists():
                    shutil.copytree(
                        source_folder,
                        output_folder,
                        dirs_exist_ok=True
                    )

                 # 给专题中的所有 HTML 页面加入统一导航
                    inject_rich_navigation(
                        output_folder,
                        title
                    )

                    print(f"已复制并关联专题页：{entry_url}")
                else:
                    print(f"警告：找不到专题源文件：{source_file}")
            else:
                print(
                    f"警告：custom_page 必须以 special/ 开头："
                    f"{entry_url}"
                )

        else:
            # 普通 Markdown 记录
            body_html = markdown.markdown(content)

            html = entry_template.replace("{{ title }}", escape(title))
            html = html.replace("{{ date }}", escape(date))
            html = html.replace("{{ categories }}", categories_html)
            html = html.replace("{{ tags }}", tags_html)
            html = html.replace("{{ content }}", body_html)

            output_file = ENTRY_OUTPUT_DIR / output_name
            output_file.write_text(html, encoding="utf-8")

            entry_url = f"entries/{output_name}"

            print(f"已生成：{output_file}")

        public_entries.append({
            "title": title,
            "date": date,
            "url": entry_url,
            "categories": categories,
            "tags": tags,
        })

    # 按日期从新到旧排列
    public_entries.sort(
        key=lambda entry: entry["date"],
        reverse=True
    )
    # 生成时间线页面
    timeline_html = timeline_template.replace(
        "{{ entries }}",
        make_entry_list(public_entries)
    )

    timeline_file = SITE_DIR / "timeline.html"
    timeline_file.write_text(timeline_html, encoding="utf-8")

    print(f"已生成时间线：{timeline_file}")
    # 生成月度归档页面
    archive_html = archive_template.replace(
        "{{ archive_content }}",
        make_archive_content(public_entries)
    )

    archive_file = SITE_DIR / "archive.html"
    archive_file.write_text(archive_html, encoding="utf-8")

    print(f"已生成月度归档：{archive_file}")
    # 生成标签页面
    tags_html = tags_template.replace(
        "{{ tags_content }}",
        make_tags_content(public_entries)
    )

    tags_file = SITE_DIR / "tags.html"
    tags_file.write_text(tags_html, encoding="utf-8")

    print(f"已生成标签页：{tags_file}")

    entry_items = []

    for entry in public_entries:
        item = f"""
<a class="entry-item" href="{entry['url']}">
    <div class="entry-title">{escape(entry['title'])}</div>
    <div class="entry-date">{escape(entry['date'])}</div>
</a>
"""
        entry_items.append(item)

    if entry_items:
        entries_html = "\n".join(entry_items)
    else:
        entries_html = "<p>目前还没有公开记录。</p>"

    index_html = index_template.replace(
        "{{ entries }}",
        entries_html
    )

    index_file = SITE_DIR / "index.html"
    index_file.write_text(index_html, encoding="utf-8")

    print(f"已生成首页：{index_file}")
    category_settings = {
        "work": {
            "name": "工作",
            "description": "工作事项、项目进度与经验记录"
        },
        "study": {
            "name": "学习",
            "description": "课程、阅读、知识和技能记录"
        },
        "life": {
            "name": "生活",
            "description": "日常生活、运动与个人体验"
        },
        "games": {
            "name": "游戏",
            "description": "游戏过程、进度与心得记录"
        }
    }

    for category_key, settings in category_settings.items():
        category_entries = []

        for entry in public_entries:
            categories = entry.get("categories", [])

            if isinstance(categories, str):
                categories = [categories]

            if category_key in categories:
                category_entries.append(entry)

        category_html = category_template.replace(
            "{{ category_name }}",
            settings["name"]
        )
        category_html = category_html.replace(
            "{{ category_description }}",
            settings["description"]
        )
        category_html = category_html.replace(
            "{{ entries }}",
            make_entry_list(category_entries)
        )

        category_file = SITE_DIR / f"{category_key}.html"
        category_file.write_text(category_html, encoding="utf-8")

        print(f"已生成分类页：{category_file}")


if __name__ == "__main__":
    build()