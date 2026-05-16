"""示例数据加载器 - 供仪表盘和匹配中心共用"""
import logging
import streamlit as st
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

logger = logging.getLogger(__name__)


def load_sample_data(force_reload: bool = False):
    """加载示例数据（并发优化版：6次LLM调用并发执行）"""
    try:
        from data.sample_data import SAMPLE_SCRIPTS, SAMPLE_LEADS

        orchestrator = st.session_state.get("orchestrator")
        if not orchestrator:
            st.error("系统未初始化，请先配置API Key")
            return

        if not force_reload:
            try:
                stats = orchestrator.db.get_dashboard_stats_optimized()
                existing_content = stats.get("content_count", 0)
                existing_leads = stats.get("lead_count", 0)
                if existing_content >= len(SAMPLE_SCRIPTS) and existing_leads >= len(SAMPLE_LEADS):
                    st.info("示例数据已加载，无需重复操作。")
                    return
            except Exception:
                pass

        progress_bar = st.empty()
        status_text = st.empty()

        try:
            bar = progress_bar.progress(0, text="正在加载示例数据...")
        except TypeError:
            bar = progress_bar.progress(0)
            status_text.caption("正在加载示例数据...")

        total = len(SAMPLE_SCRIPTS) + len(SAMPLE_LEADS)
        completed = 0
        lock = threading.Lock()

        def _analyze_script(index, sample):
            try:
                orchestrator.analyze_content(sample["script_text"])
                return index, True, sample["script_id"]
            except Exception as e:
                logger.warning("示例脚本分析失败 [%s]: %s", sample["script_id"], e)
                return index, False, f"{sample['script_id']}: {e}"

        def _analyze_lead(index, sample):
            try:
                orchestrator.analyze_lead(sample["lead_data"])
                return index, True, sample["lead_id"]
            except Exception as e:
                logger.warning("示例线索分析失败 [%s]: %s", sample["lead_id"], e)
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
                        logger.warning("示例数据加载超时: %s", tag)
                        if tag == "script":
                            st.warning("示例脚本超时")
                        else:
                            st.warning("示例线索超时")
                except Exception as e:
                    logger.warning("示例数据加载异常: %s", e)
                    with lock:
                        completed += 1

        progress_bar.empty()
        status_text.empty()
        st.success("示例数据加载完成！")
        st.rerun()
    except Exception:
        logger.error("加载示例数据失败", exc_info=True)
        st.error("加载示例数据失败，请检查网络连接后重试")