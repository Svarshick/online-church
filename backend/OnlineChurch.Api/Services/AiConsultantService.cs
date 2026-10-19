using OnlineChurch.Api.Models;

namespace OnlineChurch.Api.Services;

public class AiConsultantService(IConfiguration config)
{
    public async Task<ChatReplyResponse> GetReplyAsync(ChatMessageRequest request)
    {
        var apiKey = config["AiSettings:ApiKey"];
        
        await Task.Delay(1500);

        if (string.IsNullOrEmpty(apiKey))
        {
            return new ChatReplyResponse(
                Reply: $"[Демо-режим] Я получил ваше сообщение: «{request.Content}». Для реальных ответов настройте API-ключ ИИ в appsettings.json.",
                Mode: "demo"
            );
        }

        // TODO: Здесь будет реальный HTTP-запрос к YandexGPT/GigaChat/OpenAI
        return new ChatReplyResponse(
            Reply: "Мир вам. Это настоящий ответ от настроенной нейросети.",
            Mode: "ai"
        );
    }
}
