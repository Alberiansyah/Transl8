from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ArgosEngine:
    def __init__(self):
        self._installed_packages: dict[str, bool] = {}

    def _ensure_package(self, source_lang: str, target_lang: str) -> bool:
        key = f"{source_lang}-{target_lang}"
        if key in self._installed_packages:
            return self._installed_packages[key]

        try:
            import argostranslate.package
            argostranslate.package.update_package_index()

            available = argostranslate.package.get_available_packages()
            pkg = next(
                (p for p in available if p.from_code == source_lang and p.to_code == target_lang),
                None,
            )

            if pkg is None:
                logger.warning(f"No Argos package for {source_lang} -> {target_lang}")
                self._installed_packages[key] = False
                return False

            download_path = pkg.download()
            argostranslate.package.install_from_path(download_path)
            self._installed_packages[key] = True
            logger.info(f"Argos package installed: {source_lang} -> {target_lang}")
            return True

        except Exception as e:
            logger.error(f"Failed to install Argos package {key}: {e}")
            self._installed_packages[key] = False
            return False

    def translate_batch(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        if not self._ensure_package(source_lang, target_lang):
            return texts

        import argostranslate.translate

        results = []
        for text in texts:
            if not text.strip():
                results.append("")
                continue
            try:
                translated = argostranslate.translate.translate(text, source_lang, target_lang)
                results.append(translated)
            except Exception as e:
                logger.error(f"Argos translate failed: {e}")
                results.append(text)

        return results
