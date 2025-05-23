use base64::{engine::general_purpose::STANDARD, Engine as _};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::fs::File;
use std::io::Read as _;
use std::path::Path;

pub static VALID_EXTS: std::sync::LazyLock<HashMap<&'static str, &'static str>> =
    std::sync::LazyLock::new(|| {
        let mut map = HashMap::new();
        map.insert("jpg", "jpeg");
        map.insert("jpeg", "jpeg");
        map.insert("png", "png");
        map
    });

/*
Base64编码图像文件

Parameters
----------
image_path: &str
    图像文件路径

Returns
----------
String
    Base64编码的图像。若文件不存在，返回空字符串
*/
fn encode_image(image_path: &str) -> String {
    let mut buffer = Vec::with_capacity(1024 * 1024);
    File::open(image_path)
        .and_then(|mut f| f.read_to_end(&mut buffer))
        .map(|_| STANDARD.encode(&buffer))
        .unwrap_or_default()
}

/*
创建多模态信息

Parameters
----------
py: Python
    Python接口
image_path: &str
    图像文件路径

Returns
----------
Py<PyDict>
    python字典：多模态信息，若文件不存在，则返回空字典
*/
#[pyfunction]
pub fn chat_utils_media_handler_create_image_component(py: Python, image_path: &str) -> Py<PyDict> {
    let dict = PyDict::new(py);
    let Some(ext) = Path::new(image_path.trim_start_matches('/'))
        .extension()
        .and_then(|e| e.to_str())
    else {
        return dict.into();
    };

    let Some(mime_type) = VALID_EXTS.get(ext) else {
        return dict.into();
    };

    let encoded = encode_image(image_path);
    if encoded.is_empty() {
        return dict.into();
    }

    let image_url = PyDict::new(py);
    image_url
        .set_item("url", format!("data:image/{mime_type};base64,{encoded}"))
        .unwrap();

    dict.set_item("type", "image_url").unwrap();
    dict.set_item("image_url", image_url).unwrap();

    dict.into()
}
