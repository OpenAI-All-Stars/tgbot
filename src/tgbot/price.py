from openai.types.completion_usage import CompletionUsage

from tgbot.types import ImageSizeType


COMMISSION_COEFFICIENT = 1.2


def chatgpt_completion(usage: CompletionUsage | None) -> int:
    if not usage:
        return 0
    return int((usage.prompt_tokens * 5 + usage.completion_tokens * 15) * COMMISSION_COEFFICIENT)


def generate_image(size: ImageSizeType) -> int:
    match size:
        case '1024x1024':
            return int(40_000 * COMMISSION_COEFFICIENT)
        case '1024x1792' | '1792x1024':
            return int(80_000 * COMMISSION_COEFFICIENT)
    raise Exception('unknown size')


def audio2text(duration_s: int) -> int:
    return int(duration_s * 100 * COMMISSION_COEFFICIENT)
