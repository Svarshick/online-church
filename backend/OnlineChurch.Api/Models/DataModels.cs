using System.Text.Json.Serialization;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace OnlineChurch.Api.Models;

[Table("items")]
public class Item
{
    [Key]
    [Column("item_id")]
    [JsonPropertyName("item_id")] 
    public Guid Id { get; set; }

    [Column("title")]
    [JsonPropertyName("title")]
    public required string Title { get; set; }

    [Column("description")]
    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [Column("category")]
    [JsonPropertyName("category")]
    public required string Category { get; set; }

    [Column("price")]
    [JsonPropertyName("price")]
    public decimal Price { get; set; }

    [Column("is_available")]
    [JsonPropertyName("is_available")] // <-- ВОТ ГЛАВНОЕ ИСПРАВЛЕНИЕ
    public bool IsAvailable { get; set; }
}

public record ChatMessageRequest(
    [property: JsonPropertyName("content")] string Content, 
    [property: JsonPropertyName("history")] List<ChatTurn> History);
    
public record ChatTurn(
    [property: JsonPropertyName("role")] string Role, 
    [property: JsonPropertyName("content")] string Content);

public record ChatReplyResponse(
    [property: JsonPropertyName("reply")] string Reply, 
    [property: JsonPropertyName("mode")] string Mode);
