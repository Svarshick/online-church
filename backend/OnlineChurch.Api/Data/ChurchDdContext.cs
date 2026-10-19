using Microsoft.EntityFrameworkCore;
using OnlineChurch.Api.Models;

namespace OnlineChurch.Api.Data;

public class ChurchDbContext(DbContextOptions<ChurchDbContext> options) : DbContext(options)
{
    public DbSet<Item> Items => Set<Item>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
    }
}
