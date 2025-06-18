use core::mem;
use pulldown_cmark::{
    Alignment, BlockQuoteKind, CodeBlockKind, CowStr, Event, HeadingLevel, LinkType,
    MetadataBlockKind, Parser, Tag, TagEnd, TextMergeStream,
};
use std::borrow::Cow;
use std::fmt::Write as _;

struct LinkInfo<'a> {
    link_type: LinkType,
    dest_url: CowStr<'a>,
    title: CowStr<'a>,
    id: CowStr<'a>,
}
struct CachedState<'a> {
    // heading
    id: Option<CowStr<'a>>,
    classes: Vec<CowStr<'a>>,
    attrs: Vec<(CowStr<'a>, Option<CowStr<'a>>)>,
    // blockquote
    padding: Vec<Cow<'a, str>>,
    // code block
    code_block: Option<CodeBlockKind<'a>>,
    // list
    list_stack: Vec<Option<u64>>,
    // table
    table_alignments: Vec<Alignment>,
    // link
    link_stack: Vec<LinkInfo<'a>>,
}

fn check_event_stream(md: &str) -> Vec<String> {
    let parser = TextMergeStream::new(Parser::new_ext(&md, pulldown_cmark::Options::all()));
    let mut result_vec: Vec<String> = Vec::new();
    // text 缓存
    let mut text_string = String::new();
    // 需要保存的状态
    let mut state = CachedState {
        id: None,
        classes: vec![],
        attrs: vec![],
        padding: vec![],
        code_block: None,
        list_stack: vec![],
        table_alignments: vec![],
        link_stack: vec![],
    };
    for event in parser {
        match event {
            // Paragraph
            // Event::Start(Tag::Paragraph) => result_vec.push("\n\n".into()),
            Event::End(
                TagEnd::Paragraph
                | TagEnd::HtmlBlock
                | TagEnd::FootnoteDefinition
                | TagEnd::DefinitionList,
            ) => {
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            // Heading
            Event::Start(Tag::Heading {
                level,
                id,
                classes,
                attrs,
            }) => {
                text_string.push_str(match level {
                    HeadingLevel::H1 => "# ",
                    HeadingLevel::H2 => "## ",
                    HeadingLevel::H3 => "### ",
                    HeadingLevel::H4 => "#### ",
                    HeadingLevel::H5 => "##### ",
                    HeadingLevel::H6 => "###### ",
                });
                state.id = id;
                state.classes = classes;
                state.attrs = attrs;
            }
            Event::End(TagEnd::Heading { .. }) => {
                // 改自pulldown_cmark_to_cmark cmark_resume_one_event
                let (id, classes, attributes) = (
                    mem::take(&mut state.id),
                    mem::take(&mut state.classes),
                    mem::take(&mut state.attrs),
                );
                let emit_braces = id.is_some() || !classes.is_empty() || !attributes.is_empty();
                if emit_braces {
                    text_string.push_str(" {");
                }
                if let Some(id_str) = id {
                    /* text_string.push(' ');
                    text_string.push('#');
                    text_string.push_str(&id_str); */
                    let _ = write!(&mut text_string, " #{id_str} ");
                }
                for class in &classes {
                    /* text_string.push(' ');
                    text_string.push('.');
                    text_string.push_str(class); */
                    let _ = write!(&mut text_string, " .{class} ");
                }
                for (key, val) in &attributes {
                    /* text_string.push(' ');
                    text_string.push_str(key); */
                    let _ = write!(&mut text_string, " {key} ");
                    if let Some(val) = val {
                        /* text_string.push('=');
                        text_string.push_str(val); */
                        let _ = write!(&mut text_string, "={val}");
                    }
                }
                if emit_braces {
                    text_string.push_str(" }");
                }
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            Event::Start(Tag::BlockQuote(kind)) => {
                let every_line_padding = " > ";
                let first_line_padding = kind.map_or(every_line_padding, |kind| match kind {
                    BlockQuoteKind::Note => " > [!NOTE]",
                    BlockQuoteKind::Tip => " > [!TIP]",
                    BlockQuoteKind::Important => " > [!IMPORTANT]",
                    BlockQuoteKind::Warning => " > [!WARNING]",
                    BlockQuoteKind::Caution => " > [!CAUTION]",
                });
                text_string.push_str(first_line_padding);
                state.padding.push(Cow::Borrowed(every_line_padding));
            }
            Event::End(TagEnd::BlockQuote(_)) => {
                state.padding.pop();
                result_vec.push("\n\n".into());
            }
            // CodeBlock
            Event::Start(Tag::CodeBlock(CodeBlockKind::Indented)) => {
                state.code_block = Some(CodeBlockKind::Indented);
                state.padding.push("    ".into());
            }
            Event::Start(Tag::CodeBlock(CodeBlockKind::Fenced(info))) => {
                /* text_string.push_str("```");
                text_string.push_str(&info); */
                let _ = write!(&mut text_string, "```{info}");
                state.code_block = Some(CodeBlockKind::Fenced(info));
            }
            Event::End(TagEnd::CodeBlock) => {
                match state.code_block {
                    Some(CodeBlockKind::Fenced(..)) => {
                        text_string.push_str("```");
                        result_vec.push(mem::take(&mut text_string));
                    }
                    Some(CodeBlockKind::Indented) => {
                        state.padding.pop();
                        text_string.truncate(text_string.trim_end().len());
                        result_vec.push(mem::take(&mut text_string));
                    }
                    None => {}
                }
                state.code_block = None;
                result_vec.push("\n\n".into());
            }
            // HtmlBlock
            /* Event::End(TagEnd::HtmlBlock) => {
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            } */
            // List
            Event::Start(Tag::List(list_type)) => {
                if !state.list_stack.is_empty() {
                    state.padding.push("  ".into());
                }
                state.list_stack.push(list_type);
            }
            Event::End(TagEnd::List(_)) => {
                state.list_stack.pop();
                state.padding.pop();
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            // Item
            Event::Start(Tag::Item) => {
                if let Some(inner) = state.list_stack.last_mut() {
                    match inner {
                        Some(n) => {
                            *n += 1;
                            // text_string.push_str(format!("{n}. ").into());
                            let _ = write!(&mut text_string, "{n}. ");
                        }
                        None => {
                            let _ = write!(&mut text_string, "- ");
                        }
                    }
                }
            }
            Event::End(TagEnd::Item | TagEnd::DefinitionListTitle) => {
                text_string.push('\n');
            }
            // footnote definition
            Event::Start(Tag::FootnoteDefinition(name)) => {
                /* text_string.push_str("[^");
                text_string.push_str(&name);
                text_string.push_str("]: "); */
                let _ = write!(&mut text_string, "[^{name}]: ");
            }
            /* Event::End(TagEnd::FootnoteDefinition) => {
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            } */
            // definition list
            Event::Start(Tag::DefinitionListDefinition) => {
                state.padding.push("  : ".into());
            }
            /* Event::End(TagEnd::DefinitionListTitle) => {
                text_string.push('\n');
            } */
            Event::End(TagEnd::DefinitionListDefinition) => {
                state.padding.pop();
                text_string.push('\n');
            }
            /* Event::End(TagEnd::DefinitionList) => {
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            } */
            Event::Start(Tag::Table(alignments)) => {
                state.table_alignments = alignments;
            }
            // Event::Start(Tag::TableHead) => {}
            // Event::Start(Tag::TableRow) => {}
            Event::Start(Tag::TableCell) => {
                text_string.push('|');
            }
            Event::End(TagEnd::Table) => {
                state.table_alignments.clear();
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            // Event::End(TagEnd::TableCell) => {}
            Event::End(TagEnd::TableRow) => {
                text_string.push_str("|\n");
            }
            Event::End(TagEnd::TableHead) => {
                text_string.push_str("|\n|");
                for alignment in &state.table_alignments {
                    match alignment {
                        Alignment::None => text_string.push_str("-|"),
                        Alignment::Left => text_string.push_str(":-|"),
                        Alignment::Right => text_string.push_str("-:|"),
                        Alignment::Center => text_string.push_str(":-:|"),
                    }
                }
                text_string.push('\n');
            }
            // Emphasis
            Event::Start(Tag::Emphasis) | Event::End(TagEnd::Emphasis) => {
                text_string.push('*');
            }
            // Strong
            Event::Start(Tag::Strong) | Event::End(TagEnd::Strong) => {
                text_string.push_str("**");
            }
            // Strikethrough
            Event::Start(Tag::Strikethrough) | Event::End(TagEnd::Strikethrough) => {
                text_string.push_str("~~");
            }
            // Superscript
            Event::Start(Tag::Superscript) | Event::End(TagEnd::Superscript) => {
                text_string.push('^');
            }
            // Subscript
            Event::Start(Tag::Subscript) | Event::End(TagEnd::Subscript) => {
                text_string.push('~');
            }
            // Link & Image
            Event::Start(Tag::Link {
                link_type,
                dest_url,
                title,
                id,
            }) => {
                state.link_stack.push(LinkInfo {
                    link_type,
                    dest_url,
                    title,
                    id,
                });
                match link_type {
                    LinkType::Autolink | LinkType::Email => text_string.push('<'),
                    /* LinkType::Reference | LinkType::Collapsed | LinkType::Shortcut => {
                        text_string.push('[');
                    } */
                    _ => {
                        text_string.push('[');
                    }
                }
            }
            Event::Start(Tag::Image {
                link_type,
                dest_url,
                title,
                id,
            }) => {
                state.link_stack.push(LinkInfo {
                    link_type,
                    dest_url,
                    title,
                    id,
                });
                text_string.push_str("![");
            }
            Event::End(TagEnd::Link | TagEnd::Image) => {
                let Some(LinkInfo {
                    link_type,
                    dest_url,
                    title,
                    id,
                }) = state.link_stack.pop()
                else {
                    continue;
                };
                match link_type {
                    LinkType::Inline
                    | LinkType::ReferenceUnknown
                    | LinkType::CollapsedUnknown
                    | LinkType::ShortcutUnknown => {
                        text_string.push(']');
                        if dest_url.is_empty() || title.is_empty() {
                            continue;
                        }
                        text_string.push('(');
                        if !dest_url.is_empty() {
                            /* text_string.push('<');
                            text_string.push_str(&dest_url);
                            text_string.push('>'); */
                            let _ = write!(&mut text_string, "<{dest_url}>");
                        }
                        if !title.is_empty() {
                            /* text_string.push_str(" \"");
                            text_string.push_str(&title);
                            text_string.push('\"'); */
                            let _ = write!(&mut text_string, " \"{title}\"");
                        }
                        text_string.push(')');
                    }
                    LinkType::Reference => {
                        /* text_string.push_str("][");
                        text_string.push_str(&id);
                        text_string.push(']'); */
                        let _ = write!(&mut text_string, "][{id}]");
                    }
                    LinkType::Collapsed => {
                        text_string.push_str("][]");
                    }
                    LinkType::Shortcut => {
                        text_string.push(']');
                    }
                    LinkType::Autolink | LinkType::Email => {
                        text_string.push('>');
                    }
                    LinkType::WikiLink { .. } => {}
                }
            }
            // MetadataBlock
            Event::Start(Tag::MetadataBlock(MetadataBlockKind::YamlStyle)) => {
                text_string.push_str("---\n");
            }
            Event::Start(Tag::MetadataBlock(MetadataBlockKind::PlusesStyle)) => {
                text_string.push_str("+++\n");
            }
            Event::End(TagEnd::MetadataBlock(MetadataBlockKind::YamlStyle)) => {
                text_string.push_str("---");
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            Event::End(TagEnd::MetadataBlock(MetadataBlockKind::PlusesStyle)) => {
                text_string.push_str("+++");
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            // Text
            Event::Text(text) => {
                // text_string.push_str(&text);
                let _ = write!(&mut text_string, "{}{text}", state.padding.join(""));
            }
            // Code
            Event::Code(code) => {
                /* text_string.push('`');
                text_string.push_str(&code);
                text_string.push('`'); */
                let _ = write!(&mut text_string, "`{code}`");
            }
            // InlineMath
            Event::InlineMath(math) => {
                let _ = write!(&mut text_string, "${math}$");
            }
            // DisplayMath
            Event::DisplayMath(math) => {
                let _ = writeln!(&mut text_string, "$${math}$$");
            }
            // Html
            Event::Html(html) | Event::InlineHtml(html) => {
                text_string.push_str(&html);
            }
            // InlineHtml
            /* Event::InlineHtml(html) => {
                text_string.push_str(&html);
            } */
            // FootnoteReference
            Event::FootnoteReference(name) => {
                let _ = write!(&mut text_string, "[^{name}]");
            }
            // SoftBreak
            Event::SoftBreak => {
                text_string.push('\n');
            }
            // HardBreak
            Event::HardBreak => {
                text_string.truncate(text_string.trim_end().len());
                result_vec.push(mem::take(&mut text_string));
                result_vec.push("\n\n".into());
            }
            // Rule
            Event::Rule => {
                result_vec.push("---\n\n".into());
            }
            // TaskListMarker
            Event::TaskListMarker(checked) => {
                if checked {
                    text_string.push_str("[X] ");
                } else {
                    text_string.push_str("[ ] ");
                }
            }
            _ => {}
        }
    }
    result_vec
}
