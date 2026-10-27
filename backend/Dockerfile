# ==========================================
# Этап 1: Сборка (Build)
# Используем тяжелый образ с .NET 10 SDK для компиляции кода
# ==========================================
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Копируем только файл проекта (для кэширования слоев Docker)
COPY ["backend/OnlineChurch.Api/OnlineChurch.Api.csproj", "backend/OnlineChurch.Api/"]
RUN dotnet restore "backend/OnlineChurch.Api/OnlineChurch.Api.csproj"

# Копируем весь остальной код бекенда
COPY backend/OnlineChurch.Api/ backend/OnlineChurch.Api/
WORKDIR "/src/backend/OnlineChurch.Api"

# Компилируем проект в папку /app/publish
RUN dotnet publish "OnlineChurch.Api.csproj" -c Release -o /app/publish /p:UseAppHost=false

# ==========================================
# Этап 2: Выполнение (Runtime)
# Используем легкий образ только со средой выполнения .NET 10
# ==========================================
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app

# Открываем порт 8080 (как и было в старом Python-бекенде)
EXPOSE 8080
ENV ASPNETCORE_HTTP_PORTS=8080

# Копируем скомпилированные файлы из первого этапа
COPY --from=build /app/publish .

# Запускаем приложение
ENTRYPOINT ["dotnet", "OnlineChurch.Api.dll"]
