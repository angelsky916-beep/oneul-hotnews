# 오늘핫뉴스 자동 쇼츠

무료/오픈소스 기반 YouTube Shorts 제작 파이프라인입니다.

흐름:
1. 자동화가 당일 뉴스와 대본을 content/latest.json에 기록
2. GitHub Actions가 edge-tts + FFmpeg로 한국어 음성/자막/9:16 MP4 생성
3. GitHub Pages에 latest.mp4를 배포
4. 별도 자동화가 공개 MP4 URL을 Metricool에 전달해 YouTube Shorts로 자동 게시

민감한 API 키/토큰은 저장소 파일에 넣지 않습니다.
