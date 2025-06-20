use core::mem;
use pulldown_cmark::{
    Alignment, BlockQuoteKind, CodeBlockKind, CowStr, Event, HeadingLevel, LinkType,
    MetadataBlockKind, Parser, Tag, TagEnd, TextMergeStream,
};
use std::borrow::Cow;
use std::cmp::max;
use std::fmt::Write as _;
use std::fs::File;
use std::io::{Read, Write};
struct HeadingInfo<'a> {
    id: Option<CowStr<'a>>,
    classes: Vec<CowStr<'a>>,
    attrs: Vec<(CowStr<'a>, Option<CowStr<'a>>)>,
}
struct LinkInfo<'a> {
    link_type: LinkType,
    dest_url: CowStr<'a>,
    title: CowStr<'a>,
    id: CowStr<'a>,
}
struct CachedState<'a> {
    // heading
    heading_info: Option<HeadingInfo<'a>>,
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
    // text state
    meaningful: bool,
    has_display_math: bool,
}
#[derive(Debug, PartialEq)]
enum ChunkType {
    Text,
    Fixed,
    Delimiter,
    List,
    Table,
}

#[derive(Debug)]
enum ContentType {
    Meaningless,
    Meaningful,
    Merge,
}

#[derive(Debug)]
struct StringChunk {
    string: String,
    chunk_type: ChunkType,
    content_type: ContentType,
}
impl From<&str> for StringChunk {
    fn from(s: &str) -> Self {
        Self {
            string: s.to_string(),
            chunk_type: ChunkType::Delimiter,
            content_type: ContentType::Meaningless,
        }
    }
}
impl From<char> for StringChunk {
    fn from(c: char) -> Self {
        Self {
            string: c.to_string(),
            chunk_type: ChunkType::Delimiter,
            content_type: ContentType::Meaningless,
        }
    }
}

fn is_paragraph(s: &str) -> bool {
    let mut has_cjk;
    let mut alpha_count = 0;

    for c in s.chars() {
        // 检查中英文字符（条件一）
        has_cjk = ('\u{4E00}'..='\u{9FFF}').contains(&c);
        if has_cjk {
            return true;
        }
        alpha_count += if c.is_ascii_alphabetic() { 1 } else { 0 };
        if alpha_count >= 5 {
            return true;
        }
    }
    false
}

// 改自pulldown_cmark_to_cmark cmark_resume_one_event
fn parse_and_chunk(md: &str) -> Vec<StringChunk> {
    let parser = TextMergeStream::new(Parser::new_ext(md, pulldown_cmark::Options::all()));
    let mut result_vec: Vec<StringChunk> = Vec::new();
    // text 缓存
    let mut text_string = String::new();
    // 需要保存的状态
    let mut state = CachedState {
        heading_info: None,
        padding: vec![],
        code_block: None,
        list_stack: vec![],
        table_alignments: vec![],
        link_stack: vec![],
        meaningful: false,
        has_display_math: false,
    };
    for event in parser {
        match event {
            // Paragraph
            Event::End(TagEnd::Paragraph) => {
                text_string.truncate(text_string.trim_end().len());
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::Text
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: if state.has_display_math {
                        ContentType::Merge
                    } else if state.meaningful {
                        ContentType::Meaningful
                    } else {
                        ContentType::Meaningless
                    },
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
                state.has_display_math = false;
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
                state.heading_info = Some(HeadingInfo { id, classes, attrs });
            }
            Event::End(TagEnd::Heading { .. }) => {
                let Some(HeadingInfo {
                    ref id,
                    ref classes,
                    attrs: attributes,
                }) = state.heading_info
                else {
                    continue;
                };
                let emit_braces = id.is_some() || !classes.is_empty() || !attributes.is_empty();
                if emit_braces {
                    text_string.push_str(" {");
                }
                if let Some(id_str) = id {
                    let _ = write!(&mut text_string, " #{id_str} ");
                }
                for class in classes {
                    let _ = write!(&mut text_string, " .{class} ");
                }
                for (key, val) in attributes {
                    let _ = write!(&mut text_string, " {key} ");
                    if let Some(val) = val {
                        let _ = write!(&mut text_string, "={val}");
                    }
                }
                if emit_braces {
                    text_string.push_str(" }");
                }
                text_string.truncate(text_string.trim_end().len());
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: ChunkType::Text,
                    content_type: ContentType::Meaningless,
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.heading_info = None;
                state.meaningful = false;
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
                state.meaningful = false;
            }
            // CodeBlock
            Event::Start(Tag::CodeBlock(CodeBlockKind::Indented)) => {
                state.code_block = Some(CodeBlockKind::Indented);
                state.padding.push("    ".into());
            }
            Event::Start(Tag::CodeBlock(CodeBlockKind::Fenced(info))) => {
                let _ = write!(&mut text_string, "```{info}");
                state.code_block = Some(CodeBlockKind::Fenced(info));
            }
            Event::End(TagEnd::CodeBlock) => {
                match state.code_block {
                    Some(CodeBlockKind::Fenced(..)) => {
                        text_string.push_str("```");
                        let string_chunk = StringChunk {
                            string: mem::take(&mut text_string),
                            chunk_type: ChunkType::Fixed,
                            content_type: ContentType::Meaningless,
                        };
                        result_vec.push(string_chunk);
                    }
                    Some(CodeBlockKind::Indented) => {
                        state.padding.pop();
                        text_string.truncate(text_string.trim_end().len());
                        let string_chunk = StringChunk {
                            string: mem::take(&mut text_string),
                            chunk_type: ChunkType::Fixed,
                            content_type: ContentType::Meaningless,
                        };
                        result_vec.push(string_chunk);
                    }
                    None => {}
                }
                state.code_block = None;
                result_vec.push("\n\n".into());
                state.meaningful = false;
            }
            // HtmlBlock
            Event::End(TagEnd::HtmlBlock) => {
                text_string.truncate(text_string.trim_end().len());
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: ChunkType::Fixed,
                    content_type: ContentType::Meaningless,
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
            }
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
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::List
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: ContentType::Meaningful,
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
            }
            // Item
            Event::Start(Tag::Item) => {
                if let Some(inner) = state.list_stack.last_mut() {
                    match inner {
                        Some(n) => {
                            *n += 1;
                            let _ = write!(&mut text_string, "{n}. ");
                        }
                        None => {
                            let _ = write!(&mut text_string, "- ");
                        }
                    }
                }
            }
            Event::End(TagEnd::Item) => {
                text_string.push('\n');
            }
            // footnote definition
            Event::Start(Tag::FootnoteDefinition(name)) => {
                let _ = write!(&mut text_string, "[^{name}]: ");
            }
            Event::End(TagEnd::FootnoteDefinition) => {
                text_string.truncate(text_string.trim_end().len());
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::Text
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: if state.meaningful {
                        ContentType::Meaningful
                    } else {
                        ContentType::Meaningless
                    },
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
            }
            // definition list
            Event::Start(Tag::DefinitionListDefinition) => {
                state.padding.push("  : ".into());
            }
            Event::End(TagEnd::DefinitionListTitle) => {
                text_string.push('\n');
            }
            Event::End(TagEnd::DefinitionListDefinition) => {
                state.padding.pop();
                text_string.push('\n');
            }
            Event::End(TagEnd::DefinitionList) => {
                text_string.truncate(text_string.trim_end().len());
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::List
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: ContentType::Meaningful,
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
            }
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
                let string_chunk = StringChunk {
                    chunk_type: if is_paragraph(&text_string) {
                        ChunkType::Table
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: ContentType::Merge,
                    string: mem::take(&mut text_string),
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
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
                            let _ = write!(&mut text_string, "<{dest_url}>");
                        }
                        if !title.is_empty() {
                            let _ = write!(&mut text_string, " \"{title}\"");
                        }
                        text_string.push(')');
                    }
                    LinkType::Reference => {
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
                result_vec.push("---\n".into());
                state.meaningful = false;
            }
            Event::Start(Tag::MetadataBlock(MetadataBlockKind::PlusesStyle)) => {
                result_vec.push("+++\n".into());
                state.meaningful = false;
            }
            Event::End(TagEnd::MetadataBlock(MetadataBlockKind::YamlStyle)) => {
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::Text
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: if state.meaningful {
                        ContentType::Meaningful
                    } else {
                        ContentType::Meaningless
                    },
                };
                result_vec.push(string_chunk);
                result_vec.push("---\n\n".into());
                state.meaningful = false;
            }
            Event::End(TagEnd::MetadataBlock(MetadataBlockKind::PlusesStyle)) => {
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::Text
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: if state.meaningful {
                        ContentType::Meaningful
                    } else {
                        ContentType::Meaningless
                    },
                };
                result_vec.push(string_chunk);
                result_vec.push("+++\n\n".into());
                state.meaningful = false;
            }
            // Text
            Event::Text(text) => {
                let _ = write!(&mut text_string, "{}{text}", state.padding.join(""));
                let meaningfulness = is_paragraph(&text);
                state.meaningful |= meaningfulness;
            }
            // Code
            Event::Code(code) => {
                let _ = write!(&mut text_string, "`{code}`");
            }
            // InlineMath
            Event::InlineMath(math) => {
                let _ = write!(&mut text_string, "${math}$");
            }
            // DisplayMath
            Event::DisplayMath(math) => {
                let _ = write!(&mut text_string, "$${math}$$");
                state.has_display_math = true;
            }
            // Html
            Event::Html(html) => {
                text_string.push_str(&html);
                state.meaningful |= is_paragraph(&html);
            }
            // InlineHtml
            Event::InlineHtml(html) => {
                text_string.push_str(&html);
            }
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
                let string_chunk = StringChunk {
                    string: mem::take(&mut text_string),
                    chunk_type: if state.meaningful {
                        ChunkType::Text
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: if state.meaningful {
                        ContentType::Meaningful
                    } else {
                        ContentType::Meaningless
                    },
                };
                result_vec.push(string_chunk);
                result_vec.push("\n\n".into());
                state.meaningful = false;
            }
            // Rule
            Event::Rule => {
                result_vec.push("---\n\n".into());
                state.meaningful = false;
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

fn into_text_chunk(chunks: Vec<StringChunk>) -> Vec<(String, bool)> {
    // Split lists and tables
    let mut max_len = 0;
    let mut further_split_chunks = Vec::with_capacity(chunks.len());
    for chunk in chunks {
        match chunk.chunk_type {
            ChunkType::Text => {
                max_len = max(max_len, chunk.string.len());
                further_split_chunks.push(chunk);
            }
            ChunkType::List => {
                let list_iter = chunk.string.split('\n');
                let mut extend_vec = Vec::new();
                let mut temp_string = String::new();
                for line in list_iter {
                    if line.starts_with(' ') {
                        temp_string.push('\n');
                        temp_string.push_str(line);
                    } else {
                        temp_string.push_str(line);
                        max_len = max(max_len, temp_string.len());
                        let meaningful = is_paragraph(&temp_string);
                        let string_chunk = StringChunk {
                            string: mem::take(&mut temp_string),
                            chunk_type: if meaningful {
                                ChunkType::Text
                            } else {
                                ChunkType::Fixed
                            },
                            content_type: if meaningful {
                                ContentType::Meaningful
                            } else {
                                ContentType::Meaningless
                            },
                        };
                        if !extend_vec.is_empty() {
                            extend_vec.push('\n'.into());
                        }
                        extend_vec.push(string_chunk);
                    }
                }
                further_split_chunks.extend(extend_vec);
            }
            ChunkType::Table => {
                let mut table_iter = chunk.string.split('\n');
                let mut extend_vec = Vec::new();
                // header
                let Some(header) = table_iter.next() else {
                    further_split_chunks.extend(extend_vec);
                    continue;
                };
                max_len = max(max_len, header.len());
                let meaningful = is_paragraph(header);
                let header_chunk = StringChunk {
                    string: header.to_string(),
                    chunk_type: if meaningful {
                        ChunkType::Text
                    } else {
                        ChunkType::Fixed
                    },
                    content_type: if meaningful {
                        ContentType::Meaningful
                    } else {
                        ContentType::Meaningless
                    },
                };
                extend_vec.push(header_chunk);
                // separator
                let Some(separator) = table_iter.next() else {
                    further_split_chunks.extend(extend_vec);
                    continue;
                };
                let separator_chunk = StringChunk {
                    string: format!("\n{separator}\n"),
                    chunk_type: ChunkType::Fixed,
                    content_type: ContentType::Meaningless,
                };
                extend_vec.push(separator_chunk);
                // content
                for line in table_iter {
                    max_len = max(max_len, line.len());
                    let meaningful = is_paragraph(line);
                    let line_chunk = StringChunk {
                        string: line.to_string(),
                        chunk_type: if meaningful {
                            ChunkType::Text
                        } else {
                            ChunkType::Fixed
                        },
                        content_type: if meaningful {
                            ContentType::Meaningful
                        } else {
                            ContentType::Meaningless
                        },
                    };
                    if extend_vec.len() > 2 {
                        extend_vec.push('\n'.into());
                    }
                    extend_vec.push(line_chunk);
                }
                further_split_chunks.extend(extend_vec);
            }
            _ => {
                further_split_chunks.push(chunk);
            }
        }
    }
    // Greedy merge to chunks shorter than max_len. Each chunk must start and end on a ChunkType::Text boundary.
    let mut last_string = String::new();
    let mut temp_string = String::new();
    let mut result_vec: Vec<(String, bool)> = Vec::new();
    for chunk in further_split_chunks {
        match chunk.chunk_type {
            ChunkType::Text => {
                if temp_string.len() + chunk.string.len() <= max_len {
                    temp_string.push_str(&chunk.string);
                    last_string.clone_from(&temp_string);
                } else {
                    temp_string.drain(..last_string.len());
                    result_vec.push((mem::take(&mut last_string), true));
                    result_vec.push((mem::take(&mut temp_string), false));
                    last_string.clone_from(&chunk.string);
                    temp_string = chunk.string;
                }
            }
            ChunkType::Fixed => {
                temp_string.drain(..last_string.len());
                if !last_string.is_empty() {
                    result_vec.push((mem::take(&mut last_string), true));
                }
                if !temp_string.is_empty() {
                    result_vec.push((mem::take(&mut temp_string), false));
                }
                result_vec.push((chunk.string, false));
            }
            _ => {
                if temp_string.is_empty() {
                    result_vec.push((chunk.string, false));
                } else {
                    temp_string.push_str(&chunk.string);
                }
            }
        }
    }
    result_vec
}
