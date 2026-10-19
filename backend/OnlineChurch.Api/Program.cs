using Microsoft.EntityFrameworkCore;
using OnlineChurch.Api.Data;
using OnlineChurch.Api.Models;
using OnlineChurch.Api.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<ChurchDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

builder.Services.AddSingleton<AiConsultantService>();

builder.Services.AddCors(options =>
{
    options.AddPolicy("ReactApp", policy =>
    {
        policy.WithOrigins("http://localhost:3000", "http://127.0.0.1:3000")
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();
app.UseCors("ReactApp");

var api = app.MapGroup("/api/v1");

api.MapGet("/items", async (ChurchDbContext db) =>
{
    var items = await db.Items
        .Where(i => i.IsAvailable)
        .ToListAsync();
        
    return Results.Ok(items);
});

api.MapPost("/chats/messages", async (ChatMessageRequest request, AiConsultantService aiService) =>
{
    if (string.IsNullOrWhiteSpace(request.Content) || request.Content.Length > 2000)
    {
        return Results.Json(new { detail = "Сообщение не принято сервером: оно пустое или слишком длинное." }, statusCode: 422);
    }

    var response = await aiService.GetReplyAsync(request);
    return Results.Ok(response);
});

app.Run();
