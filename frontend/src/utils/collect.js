/**
 * F7 前端工具函数:文件格式/大小校验、文件收集、百分比格式化
 *
 * 依据:doc/high-level-design.md §3.3(F7)、§4.2(2)、§6
 * 约定:纯工具函数,不涉及组件与请求;不直接弹 UI 提示,
 *      需要提示的场景以返回值语义表达(如返回空数组),文案由调用方视图组件负责。
 * 说明:F4/F5 的校验与收集逻辑全部复用本模块。
 */

/** 支持的图片扩展名(统一小写,文件名扩展名小写化后与之比较) */
export const SUPPORTED_EXTS = ['.jpg', '.jpeg', '.png', '.bmp'];

/** 单张图片大小上限:10MB(与后端 M1 常量一致,双重校验) */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;

/**
 * 校验文件名是否为支持的图片格式。
 * 扩展名小写化后判断是否属于 .jpg/.jpeg/.png/.bmp,
 * 大小写混合的文件名(如 A.JPG、b.Png)同样通过。
 * @param {string} filename 文件名
 * @returns {boolean} 是否支持
 */
export function is_supported(filename) {
  if (typeof filename !== 'string' || filename.length === 0) return false;
  const dot = filename.lastIndexOf('.');
  // 无扩展名(不含 '.' 或以 '.' 结尾)视为不支持
  if (dot < 0 || dot === filename.length - 1) return false;
  const ext = filename.slice(dot).toLowerCase();
  return SUPPORTED_EXTS.includes(ext);
}

/**
 * 校验文件大小是否合规:≤ 10MB(与后端 M1 常量一致)。
 * @param {File} file 文件对象(需含 size 属性,单位字节)
 * @returns {boolean} 大小是否 ≤ 10MB
 */
export function check_size(file) {
  if (!file || typeof file.size !== 'number') return false;
  return file.size <= MAX_FILE_SIZE;
}

/**
 * 从 FileList 中过滤出支持的图片文件,返回 File 数组。
 * 不支持的项由调用方负责提示,本函数保持纯函数、不弹提示。
 * @param {FileList} fileList 文件输入框的 files(FileList 或类数组对象)
 * @returns {File[]} 扩展名属于 jpg/jpeg/png/bmp 的图片文件数组
 */
export function collect_files(fileList) {
  if (!fileList || typeof fileList.length !== 'number') return [];
  return Array.from(fileList).filter((file) => is_supported(file.name));
}

/**
 * 收集文件夹输入(webkitdirectory)中的全部图片。
 * 实现要点:input.files 的 webkitRelativePath 已包含子目录递归结果,
 * 直接遍历 input.files 过滤即可,无需自行递归。
 * 浏览器不支持 webkitdirectory(如 Firefox)时返回空数组,
 * 由调用方提示降级为多选文件(本函数不直接弹 UI 提示)。
 * @param {HTMLInputElement} inputElement 带 webkitdirectory 属性的 file 输入框
 * @returns {File[]} 收集到的图片文件数组;不支持或未选中时返回 []
 */
export function collect_folder_files(inputElement) {
  // 不支持 webkitdirectory 的浏览器上该属性不存在或为假,直接返回空数组
  if (!inputElement || !('webkitdirectory' in inputElement) || !inputElement.webkitdirectory) {
    return [];
  }
  const files = inputElement.files;
  if (!files || typeof files.length !== 'number' || files.length === 0) return [];
  const result = [];
  for (const file of files) {
    // webkitRelativePath 含递归子目录路径(如 子目录/a.jpg);
    // 缺失说明浏览器未真正启用目录选择(降级为普通文件选择),跳过
    const rel = file.webkitRelativePath;
    if (!rel) continue;
    if (is_supported(rel)) result.push(file);
  }
  return result;
}

/**
 * 0~1 的概率值转百分比字符串,保留 1 位小数。
 * 示例:0.924 -> '92.4%',0.5 -> '50.0%'。
 * @param {number} p 概率值(0~1)
 * @returns {string} 形如 '92.4%' 的文本;非数值返回空字符串
 */
export function format_percent(p) {
  // 空值(如批量结果中失败行的 confidence 为 null)返回空串,供视图层降级显示 '-'
  if (p === null || p === undefined || p === '') return '';
  const n = Number(p);
  // 非有限数值(如 NaN)同样返回空串
  if (!Number.isFinite(n)) return '';
  return (n * 100).toFixed(1) + '%';
}
