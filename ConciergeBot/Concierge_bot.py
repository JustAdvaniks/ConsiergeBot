import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = '!'
intents = discord.Intents().all()

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Словарь для хранения сообщений и соответствующих ролей
role_reactions = {}

# Словарь для хранения временных данных настройки
setup_sessions = {}

class RoleSetupSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.title = "🎮 Выбор ролей"
        self.description = "Выберите роли, нажав на соответствующие реакции:"
        self.color = 0x7289da
        self.roles = []  # Список словарей: {"emoji": "", "role": None, "description": ""}
        self.state = "title"  # title, description, color, adding_roles, complete
        self.message = None

@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} успешно запущен!')
    print(f'ID бота: {bot.user.id}')


@bot.command(name='setup_roles')
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    """Запускает интерактивную настройку сообщения для выдачи ролей"""

    if ctx.author.id in setup_sessions:
        await ctx.send("У вас уже есть активная сессия настройки!")
        return

    session = RoleSetupSession(ctx.author.id)
    setup_sessions[ctx.author.id] = session

    embed = discord.Embed(
        title="🎮 Настройка выдачи ролей",
        description="Давайте настроим сообщение для выдачи ролей!",
        color=0x00ff00
    )

    embed.add_field(
        name="Шаг 1: Заголовок",
        value="Введите заголовок для сообщения (или 'пропустить' для значения по умолчанию):",
        inline=False
    )

    session.message = await ctx.send(embed=embed)




@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    # Проверяем, есть ли активная сессия настройки у пользователя
    if message.author.id in setup_sessions:
        session = setup_sessions[message.author.id]
        content = message.content

        try:
            if session.state == "title":
                if content.lower() != 'пропустить':
                    session.title = content

                embed = discord.Embed(
                    title="🎮 Настройка выдачи ролей",
                    description="Отлично! Теперь настройте описание:",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Шаг 2: Описание",
                    value="Введите описание для сообщения (или 'пропустить' для значения по умолчанию):",
                    inline=False
                )
                await session.message.edit(embed=embed)
                session.state = "description"

            elif session.state == "description":
                if content.lower() != 'пропустить':
                    session.description = content

                embed = discord.Embed(
                    title="🎮 Настройка выдачи ролей",
                    description="Теперь давайте добавим роли!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Шаг 3: Добавление ролей",
                    value="Введите роль в формате: `@роль эмодзи описание`\n\nПример: `@Геймер 🎮 Любите играть в игры`\n\nКогда закончите, напишите **'готово'**",
                    inline=False
                )
                await session.message.edit(embed=embed)
                session.state = "adding_roles"

            elif session.state == "adding_roles":
                if content.lower() == 'готово':
                    if not session.roles:
                        await message.channel.send("Нужно добавить хотя бы одну роль! Продолжайте добавление.")
                        return

                    # Создаем финальное сообщение
                    embed = discord.Embed(
                        title=session.title,
                        description=session.description,
                        color=session.color
                    )

                    role_text = ""
                    for role_data in session.roles:
                        role_text += f"{role_data['emoji']} - {role_data['role'].mention}: {role_data['description']}\n"

                    embed.add_field(name="Доступные роли:", value=role_text, inline=False)
                    embed.set_footer(text="Нажмите на реакции ниже чтобы получить роли")

                    final_message = await message.channel.send(embed=embed)

                    # Добавляем реакции и сохраняем конфигурацию
                    role_reactions[final_message.id] = {}

                    for role_data in session.roles:
                        role_reactions[final_message.id][role_data['emoji']] = role_data['role'].id
                        await final_message.add_reaction(role_data['emoji'])

                    # Завершаем сессию
                    del setup_sessions[message.author.id]

                    success_embed = discord.Embed(
                        title="✅ Настройка завершена!",
                        description=f"Сообщение для выдачи ролей создано!\nID сообщения: {final_message.id}",
                        color=0x00ff00
                    )
                    await message.channel.send(embed=success_embed)

                else:
                    # Парсим ввод роли
                    parts = content.split(' ', 2)
                    if len(parts) < 3:
                        await message.channel.send("❌ Неправильный формат! Используйте: `@роль эмодзи описание`")
                        return

                    role_mention, emoji, description = parts

                    # Получаем роль из упоминания
                    if not message.role_mentions:
                        await message.channel.send("❌ Роль не найдена! Упомяните роль правильно.")
                        return

                    role = message.role_mentions[0]

                    # Проверяем эмодзи
                    if len(emoji) > 5:  # Простая проверка на эмодзи
                        await message.channel.send("❌ Используйте стандартные эмодзи Discord!")
                        return

                    # Добавляем роль в сессию
                    session.roles.append({
                        "emoji": emoji,
                        "role": role,
                        "description": description
                    })

                    # Показываем текущий список ролей
                    embed = discord.Embed(
                        title="🎮 Настройка выдачи ролей",
                        description="Роль добавлена! Текущий список:",
                        color=0x00ff00
                    )

                    role_list = ""
                    for i, role_data in enumerate(session.roles, 1):
                        role_list += f"{i}. {role_data['emoji']} - {role_data['role'].mention}: {role_data['description']}\n"

                    embed.add_field(name="Добавленные роли:", value=role_list or "Пока нет ролей", inline=False)
                    embed.add_field(
                        name="Следующий шаг:",
                        value="Добавьте еще роли в том же формате или напишите **'готово'** для завершения",
                        inline=False
                    )

                    await session.message.edit(embed=embed)

        except Exception as e:
            await message.channel.send(f"❌ Произошла ошибка: {e}")
            if message.author.id in setup_sessions:
                del setup_sessions[message.author.id]

        await message.delete()

    await bot.process_commands(message)


@bot.command(name='quick_setup')
@commands.has_permissions(administrator=True)
async def quick_setup(ctx, *, config: str):
    """Быстрая настройка через одну команду"""

    try:
        # Парсим конфигурацию: "Заголовок | Описание | @роль1 эмодзи1 описание1, @роль2 эмодзи2 описание2"
        parts = config.split('|', 2)
        if len(parts) < 3:
            await ctx.send(
                "❌ Неправильный формат! Используйте: `!quick_setup Заголовок | Описание | @роль1 эмодзи1 описание1, @роль2 эмодзи2 описание2`")
            return

        title = parts[0].strip()
        description = parts[1].strip()
        roles_config = parts[2].strip()

        # Парсим роли
        roles_data = []
        role_entries = roles_config.split(',')

        for entry in role_entries:
            entry = entry.strip()
            if not entry:
                continue

            # Используем временное сообщение для парсинга упоминаний
            temp_msg = await ctx.send(entry)
            await temp_msg.delete()

            # Получаем упомянутые роли
            if not temp_msg.role_mentions:
                await ctx.send(f"❌ Роль не найдена в: {entry}")
                return

            role = temp_msg.role_mentions[0]

            # Удаляем упоминание роли из строки и парсим остальное
            remaining = entry.replace(f'<@&{role.id}>', '').strip()
            emoji_part = remaining.split(' ', 1)

            if len(emoji_part) < 2:
                await ctx.send(f"❌ Неправильный формат для роли {role.name}")
                return

            emoji = emoji_part[0]
            role_description = emoji_part[1]

            roles_data.append({
                "emoji": emoji,
                "role": role,
                "description": role_description
            })

        # Создаем сообщение
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x7289da
        )

        role_text = ""
        for role_data in roles_data:
            role_text += f"{role_data['emoji']} - {role_data['role'].mention}: {role_data['description']}\n"

        embed.add_field(name="Доступные роли:", value=role_text, inline=False)
        embed.set_footer(text="Нажмите на реакции ниже чтобы получить роли")

        final_message = await ctx.send(embed=embed)

        # Добавляем реакции и сохраняем конфигурацию
        role_reactions[final_message.id] = {}

        for role_data in roles_data:
            role_reactions[final_message.id][role_data['emoji']] = role_data['role'].id
            await final_message.add_reaction(role_data['emoji'])

        success_embed = discord.Embed(
            title="✅ Настройка завершена!",
            description=f"Сообщение для выдачи ролей создано!\nID сообщения: {final_message.id}",
            color=0x00ff00
        )
        await ctx.send(embed=success_embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")


@bot.command(name='cancel_setup')
@commands.has_permissions(administrator=True)
async def cancel_setup(ctx):
    """Отменяет активную сессию настройки"""
    if ctx.author.id in setup_sessions:
        del setup_sessions[ctx.author.id]
        await ctx.send("✅ Сессия настройки отменена!")
    else:
        await ctx.send("❌ У вас нет активной сессии настройки!")


@bot.event
async def on_raw_reaction_add(payload):
    """Обрабатывает добавление реакции"""
    if payload.user_id == bot.user.id:
        return

    message_id = payload.message_id
    emoji = str(payload.emoji)

    if message_id in role_reactions and emoji in role_reactions[message_id]:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role_id = role_reactions[message_id][emoji]
        role = guild.get_role(role_id)

        if role and member:
            try:
                await member.add_roles(role)
                print(f"Выдана роль {role.name} пользователю {member.display_name}")
            except discord.Forbidden:
                print("Недостаточно прав для выдачи роли")
            except Exception as e:
                print(f"Ошибка при выдаче роли: {e}")



@bot.event
async def on_raw_reaction_remove(payload):
    """Обрабатывает удаление реакции"""
    if payload.user_id == bot.user.id:
        return

    message_id = payload.message_id
    emoji = str(payload.emoji)

    if message_id in role_reactions and emoji in role_reactions[message_id]:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role_id = role_reactions[message_id][emoji]
        role = guild.get_role(role_id)

        if role and member:
            try:
                await member.remove_roles(role)
                print(f"Удалена роль {role.name} у пользователя {member.display_name}")
            except discord.Forbidden:
                print("Недостаточно прав для удаления роли")
            except Exception as e:
                print(f"Ошибка при удалении роли: {e}")



@bot.command(name='clear_roles')
@commands.has_permissions(administrator=True)
async def clear_roles(ctx, message_id: int):
    """Удаляет сообщение из системы выдачи ролей"""
    if message_id in role_reactions:
        del role_reactions[message_id]
        await ctx.send(f"✅ Сообщение {message_id} удалено из системы ролей")
    else:
        await ctx.send("❌ Сообщение не найдено в системе ролей")



@bot.command(name='list_roles')
@commands.has_permissions(administrator=True)
async def list_roles(ctx):
    """Показывает все настроенные сообщения для выдачи ролей"""
    if not role_reactions:
        await ctx.send("ℹ️ Нет настроенных сообщений для выдачи ролей")
        return

    embed = discord.Embed(title="📊 Настроенные сообщения для выдачи ролей", color=0x7289da)

    for message_id, reactions in role_reactions.items():
        reaction_text = ""
        for emoji, role_id in reactions.items():
            role = ctx.guild.get_role(role_id)
            if role:
                reaction_text += f"{emoji} → {role.name}\n"

        embed.add_field(
            name=f"Сообщение ID: {message_id}",
            value=reaction_text or "Нет реакций",
            inline=False
        )

    await ctx.send(embed=embed)



@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("У вас недостаточно прав для выполнения этой команды!")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("Роль не найдена! Убедитесь, что вы правильно указали роль.")
    else:
        await ctx.send(f"Произошла ошибка: {error}")



bot.run(TOKEN)
