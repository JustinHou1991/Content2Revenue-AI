"""示例数据加载器 - 供仪表盘和匹配中心共用"""
import streamlit as st
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError


def load_sample_data():
    """加载示例数据（并发优化版：6次LLM调用并发执行）"""
    try:
        from data.sample_data import SAMPLE_SCRIPTS, SAMPLE_LEADS

        progress_bar = st.empty()
        status_text = st.empty()

        try:
            bar = progress_bar.progress(0, text="正在加载示例数据...")
        except TypeError:
            bar = progress_bar.progress(0)
            status_text.caption("正在加载示例数据...")

        orchestrator = st.session_state.get("orchestrator")
        if not orchestrator:
            st.error("系统未初始化，请先配置API Key")
            return

        total = len(SAMPLE_SCRIPTS) + len(SAMPLE_LEADS)
        completed = 0
        lock = threading.Lock()

        def _analyze_script(index, sample):
            try:
                orchestrator.analyze_content(sample["script_text"])
                return index, True, sample["script_id"]
            except Exception as e:
                return index, False, f"{sample['script_id']}: {e}"

        def _analyze_lead(index, sample):
            try:
                orchestrator.analyze_lead(sample["lead_data"])
                return index, True, sample["lead_id"]
            except Exception as e:
                return index, False, f"{sample['lead_id']}: {e}"

        all_futures = {}

        with ThreadPoolExecutor(max_workers=min(8, total)) as executor:
            for i, sample in enumerate(SAMPLE_SCRIPTS):
                all_futures[executor.submit(_analyze_script, i, sample)] = ("script", i)

            offset = len(SAMPLE_SCRIPTS)
            for j, sample in enumerate(SAMPLE_LEADS):
                all_futures[executor.submit(_analyze_lead, j, sample)] = ("lead", offset + j)

            for future in as_completed(all_futures):
                tag, pos = all_futures[future]
                try:
                    idx, success, label = future.result(timeout=300)
                    with lock:
                        completed += 1
                        pct = completed / total
                        try:
                            bar.progress(pct, text=f"加载示例数据... {completed}/{total}")
                        except TypeError:
                            bar.progress(pct)
                except TimeoutError:
                    with lock:
                        completed += 1
                        if tag == "script":
                            st.warning("示例脚本超时")
                        else:
                            st.warning("示例线索超时")
                except Exception:
                    with lock:
                        completed += 1

        progress_bar.empty()
        status_text.empty()
        st.success("示例数据加载完成！")
        st.rerun()
    except Exception:
        st.error("加载示例数据失败，请检查网络连接后重试")