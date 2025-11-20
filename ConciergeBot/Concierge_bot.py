import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import re

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PREFIX = '//'
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


def parse_emoji(emoji_str, guild):
    """Парсит эмодзи из строки, поддерживает кастомные и стандартные эмодзи"""
    # Проверяем на кастомный эмодзи в формате <:name:id> или <a:name:id>
    custom_emoji_match = re.match(r'<a?:([a-zA-Z0-9_]+):(\d+)>', emoji_str)
    if custom_emoji_match:
        emoji_name, emoji_id = custom_emoji_match.groups()
        emoji = discord.utils.get(guild.emojis, id=int(emoji_id))
        if emoji:
            return emoji
        else:
            return None

    # Проверяем на стандартный эмодзи
    elif len(emoji_str) <= 5:
        return emoji_str

    return None


async def add_reaction_to_message(message, emoji):
    """Добавляет реакцию к сообщению, поддерживая кастомные эмодзи"""
    try:
        if isinstance(emoji, discord.Emoji):
            await message.add_reaction(emoji)
        else:
            await message.add_reaction(str(emoji))
    except discord.HTTPException as e:
        raise commands.CommandError(f"Не удалось добавить реакцию {emoji}: {e}")


@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} успешно запущен!')
    print(f'ID бота: {bot.user.id}')


@bot.command(name='setup_roles',help='Запускает интерактивную настройку сообщения для выдачи ролей')
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):

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
                    value="Введите роль в формате: `@роль эмодзи описание`\n\n**Поддерживаются:**\n- Стандартные эмодзи: 🎮\n- Кастомные эмодзи: <:emoji_name:emoji_id> или :emoji_name:\n\nПример: `@Геймер 🎮 Любите играть в игры`\n`@Дизайнер :custom_emoji: Для творческих людей`\n\nКогда закончите, напишите **'готово'**",
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
                        emoji_display = role_data['emoji']
                        if isinstance(emoji_display, discord.Emoji):
                            emoji_display = str(emoji_display)  # Показываем как <:name:id>

                        role_text += f"{emoji_display} - {role_data['role'].mention}: {role_data['description']}\n"

                    embed.add_field(name="Доступные роли:", value=role_text, inline=False)
                    embed.set_footer(text="Нажмите на реакции ниже чтобы получить роли")

                    final_message = await message.channel.send(embed=embed)

                    # Добавляем реакции и сохраняем конфигурацию
                    role_reactions[final_message.id] = {}

                    for role_data in session.roles:
                        # Сохраняем эмодзи в формате, который можно использовать в on_raw_reaction_add
                        emoji_key = str(role_data['emoji'].id) if isinstance(role_data['emoji'], discord.Emoji) else \
                        role_data['emoji']
                        role_reactions[final_message.id][emoji_key] = role_data['role'].id

                        await add_reaction_to_message(final_message, role_data['emoji'])

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

                    role_mention, emoji_str, description = parts

                    # Получаем роль из упоминания
                    if not message.role_mentions:
                        await message.channel.send("❌ Роль не найдена! Упомяните роль правильно.")
                        return

                    role = message.role_mentions[0]

                    # Парсим эмодзи
                    emoji = parse_emoji(emoji_str, message.guild)
                    if not emoji:
                        # Попробуем найти кастомный эмодзи по имени
                        if emoji_str.startswith(':') and emoji_str.endswith(':'):
                            emoji_name = emoji_str[1:-1]
                            emoji = discord.utils.get(message.guild.emojis, name=emoji_name)

                    if not emoji:
                        await message.channel.send(
                            "❌ Эмодзи не найден! Используйте стандартные эмодзи или кастомные эмодзи этого сервера.")
                        return

                    # Проверяем, что бот может использовать этот эмодзи
                    try:
                        test_msg = await message.channel.send("Проверка эмодзи...")
                        await add_reaction_to_message(test_msg, emoji)
                        await test_msg.delete()
                    except:
                        await message.channel.send(
                            "❌ Бот не может использовать этот эмодзи! Убедитесь, что эмодзи принадлежит этому серверу и у бота есть доступ.")
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
                        emoji_display = role_data['emoji']
                        if isinstance(emoji_display, discord.Emoji):
                            emoji_display = str(emoji_display)

                        role_list += f"{i}. {emoji_display} - {role_data['role'].mention}: {role_data['description']}\n"

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


@bot.command(name='quick_setup',help='Быстрая настройка через одну команду с поддержкой кастомных эмодзи')
@commands.has_permissions(administrator=True)
async def quick_setup(ctx, *, config: str):

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

            # Получаем упомянутые роли
            if not temp_msg.role_mentions:
                await temp_msg.delete()
                await ctx.send(f"❌ Роль не найдена в: {entry}")
                return

            role = temp_msg.role_mentions[0]

            # Удаляем упоминание роли из строки и парсим остальное
            remaining = entry.replace(f'<@&{role.id}>', '').strip()
            emoji_part = remaining.split(' ', 1)

            if len(emoji_part) < 2:
                await temp_msg.delete()
                await ctx.send(f"❌ Неправильный формат для роли {role.name}")
                return

            emoji_str = emoji_part[0]
            role_description = emoji_part[1]

            # Парсим эмодзи
            emoji = parse_emoji(emoji_str, ctx.guild)
            if not emoji:
                # Попробуем найти кастомный эмодзи по имени
                if emoji_str.startswith(':') and emoji_str.endswith(':'):
                    emoji_name = emoji_str[1:-1]
                    emoji = discord.utils.get(ctx.guild.emojis, name=emoji_name)

            if not emoji:
                await temp_msg.delete()
                await ctx.send(
                    f"❌ Эмодзи не найден для роли {role.name}! Используйте стандартные эмодзи или кастомные эмодзи этого сервера.")
                return

            # Проверяем, что бот может использовать этот эмодзи
            try:
                await add_reaction_to_message(temp_msg, emoji)
            except:
                await temp_msg.delete()
                await ctx.send(f"❌ Бот не может использовать эмодзи {emoji_str} для роли {role.name}!")
                return

            await temp_msg.delete()

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
            emoji_display = role_data['emoji']
            if isinstance(emoji_display, discord.Emoji):
                emoji_display = str(emoji_display)

            role_text += f"{emoji_display} - {role_data['role'].mention}: {role_data['description']}\n"

        embed.add_field(name="Доступные роли:", value=role_text, inline=False)
        embed.set_footer(text="Нажмите на реакции ниже чтобы получить роли")

        final_message = await ctx.send(embed=embed)

        # Добавляем реакции и сохраняем конфигурацию
        role_reactions[final_message.id] = {}

        for role_data in roles_data:
            # Сохраняем эмодзи в формате, который можно использовать в on_raw_reaction_add
            emoji_key = str(role_data['emoji'].id) if isinstance(role_data['emoji'], discord.Emoji) else role_data[
                'emoji']
            role_reactions[final_message.id][emoji_key] = role_data['role'].id

            await add_reaction_to_message(final_message, role_data['emoji'])

        success_embed = discord.Embed(
            title="✅ Настройка завершена!",
            description=f"Сообщение для выдачи ролей создано!\nID сообщения: {final_message.id}",
            color=0x00ff00
        )
        await ctx.send(embed=success_embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")


@bot.event
async def on_raw_reaction_add(payload):
    """Обрабатывает добавление реакции для кастомных и стандартных эмодзи"""
    if payload.user_id == bot.user.id:
        return

    message_id = payload.message_id
    emoji = payload.emoji

    # Создаем ключ для поиска в словаре
    if emoji.is_custom_emoji():
        emoji_key = str(emoji.id)  # Для кастомных эмодзи используем ID
    else:
        emoji_key = str(emoji)  # Для стандартных эмодзи используем строку

    if message_id in role_reactions and emoji_key in role_reactions[message_id]:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role_id = role_reactions[message_id][emoji_key]
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
    """Обрабатывает удаление реакции для кастомных и стандартных эмодзи"""
    if payload.user_id == bot.user.id:
        return

    message_id = payload.message_id
    emoji = payload.emoji

    # Создаем ключ для поиска в словаре (такой же как в on_raw_reaction_add)
    if emoji.is_custom_emoji():
        emoji_key = str(emoji.id)
    else:
        emoji_key = str(emoji)

    if message_id in role_reactions and emoji_key in role_reactions[message_id]:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role_id = role_reactions[message_id][emoji_key]
        role = guild.get_role(role_id)

        if role and member:
            try:
                await member.remove_roles(role)
                print(f"Удалена роль {role.name} у пользователя {member.display_name}")
            except discord.Forbidden:
                print("Недостаточно прав для удаления роли")
            except Exception as e:
                print(f"Ошибка при удалении роли: {e}")


# Остальные команды (cancel_setup, clear_roles, list_roles) остаются без изменений

@bot.command(name='cancel_setup',help='Отменяет активную сессию настройки')
@commands.has_permissions(administrator=True)
async def cancel_setup(ctx):
    if ctx.author.id in setup_sessions:
        del setup_sessions[ctx.author.id]
        await ctx.send("✅ Сессия настройки отменена!")
    else:
        await ctx.send("❌ У вас нет активной сессии настройки!")


@bot.command(name='clear_roles',help='Удаляет сообщение из системы выдачи ролей (Укажите message_id)')
@commands.has_permissions(administrator=True)
async def clear_roles(ctx, message_id: int):
    if message_id in role_reactions:
        del role_reactions[message_id]
        await ctx.send(f"✅ Сообщение {message_id} удалено из системы ролей")
    else:
        await ctx.send("❌ Сообщение не найдено в системе ролей")


@bot.command(name='list_roles',help='Показывает все настроенные сообщения для выдачи ролей')
@commands.has_permissions(administrator=True)
async def list_roles(ctx):
    if not role_reactions:
        await ctx.send("ℹ️ Нет настроенных сообщений для выдачи ролей")
        return

    embed = discord.Embed(title="📊 Настроенные сообщения для выдачи ролей", color=0x7289da)

    for message_id, reactions in role_reactions.items():
        reaction_text = ""
        for emoji_key, role_id in reactions.items():
            role = ctx.guild.get_role(role_id)
            if role:
                # Для кастомных эмодзи пытаемся найти и отобразить их
                try:
                    emoji_id = int(emoji_key)
                    emoji = ctx.guild.get_emoji(emoji_id)
                    if emoji:
                        reaction_text += f"{emoji} → {role.name}\n"
                    else:
                        reaction_text += f"[Custom:{emoji_key}] → {role.name}\n"
                except ValueError:
                    # Это стандартный эмодзи
                    reaction_text += f"{emoji_key} → {role.name}\n"

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


@bot.command(name='restore_roles',help='Восстанавливает сообщение в систему выдачи ролей (Укажите message_id)')
@commands.has_permissions(administrator=True)
async def restore_roles(ctx, message_id: int):
    try:
        # Получаем сообщение по ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Сообщение с указанным ID не найдено в этом канале!")
            return
        except discord.Forbidden:
            await ctx.send("❌ Нет прав для доступа к этому сообщению!")
            return

        # Проверяем, что сообщение уже не в системе
        if message_id in role_reactions:
            await ctx.send("❌ Это сообщение уже находится в системе ролей!")
            return

        # Анализируем embed сообщения
        if not message.embeds:
            await ctx.send("❌ У сообщения нет embed для анализа!")
            return

        embed = message.embeds[0]

        # Парсим роли из embed
        roles_data = []

        # Ищем поле с ролями
        roles_field = None
        for field in embed.fields:
            if "рол" in field.name.lower() or "role" in field.name.lower():
                roles_field = field
                break

        if not roles_field:
            await ctx.send("❌ Не удалось найти поле с ролями в embed сообщения!")
            return

        # Парсим каждую строку с ролью
        role_lines = roles_field.value.split('\n')
        for line in role_lines:
            line = line.strip()
            if not line or ' - ' not in line:
                continue

            # Парсим эмодзи и описание роли
            parts = line.split(' - ', 1)
            if len(parts) < 2:
                continue

            emoji_part, role_part = parts

            # Парсим эмодзи
            emoji = parse_emoji(emoji_part.strip(), ctx.guild)
            if not emoji:
                # Пробуем найти по имени если это кастомный эмодзи в текстовом формате
                custom_match = re.match(r'<a?:([a-zA-Z0-9_]+):(\d+)>', emoji_part.strip())
                if custom_match:
                    emoji_name, emoji_id = custom_match.groups()
                    emoji = discord.utils.get(ctx.guild.emojis, id=int(emoji_id))

            if not emoji:
                await ctx.send(f"❌ Не удалось распознать эмодзи: {emoji_part}")
                continue

            # Парсим роль из упоминания
            role_match = re.search(r'<@&(\d+)>', role_part)
            if not role_match:
                await ctx.send(f"❌ Не удалось найти упоминание роли в: {role_part}")
                continue

            role_id = int(role_match.group(1))
            role = ctx.guild.get_role(role_id)

            if not role:
                await ctx.send(f"❌ Роль с ID {role_id} не найдена на сервере!")
                continue

            # Извлекаем описание (все что после упоминания роли)
            description = role_part.split(':', 1)[1].strip() if ':' in role_part else "Без описания"

            roles_data.append({
                "emoji": emoji,
                "role": role,
                "description": description
            })

        if not roles_data:
            await ctx.send("❌ Не удалось распознать ни одной роли в сообщении!")
            return

        # Восстанавливаем реакции
        role_reactions[message_id] = {}

        for role_data in roles_data:
            # Сохраняем в систему
            emoji_key = str(role_data['emoji'].id) if isinstance(role_data['emoji'], discord.Emoji) else role_data[
                'emoji']
            role_reactions[message_id][emoji_key] = role_data['role'].id

            # Добавляем реакцию если её нет
            try:
                reaction_exists = False
                for reaction in message.reactions:
                    reaction_emoji = str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else str(reaction.emoji)
                    if reaction_emoji == emoji_key:
                        reaction_exists = True
                        break

                if not reaction_exists:
                    await add_reaction_to_message(message, role_data['emoji'])
            except Exception as e:
                await ctx.send(f"⚠️ Не удалось добавить реакцию {emoji_key}: {e}")

        success_embed = discord.Embed(
            title="✅ Восстановление завершено!",
            description=f"Сообщение {message_id} успешно восстановлено в системе ролей!\n\n**Восстановлено ролей:** {len(roles_data)}",
            color=0x00ff00
        )

        # Показываем восстановленные роли
        role_list = ""
        for role_data in roles_data:
            emoji_display = role_data['emoji']
            if isinstance(emoji_display, discord.Emoji):
                emoji_display = str(emoji_display)
            role_list += f"{emoji_display} - {role_data['role'].mention}\n"

        success_embed.add_field(name="Восстановленные роли:", value=role_list, inline=False)
        await ctx.send(embed=success_embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка при восстановлении: {e}")


@bot.command(name='restore_from_reactions',help='Восстанавливает систему ролей на основе существующих реакций сообщения (Укажите message_id)')
@commands.has_permissions(administrator=True)
async def restore_from_reactions(ctx, message_id: int):
    try:
        # Получаем сообщение по ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Сообщение с указанным ID не найдено в этом канале!")
            return

        # Проверяем, что сообщение уже не в системе
        if message_id in role_reactions:
            await ctx.send("❌ Это сообщение уже находится в системе ролей!")
            return

        # Анализируем реакции
        if not message.reactions:
            await ctx.send("❌ На сообщении нет реакций!")
            return

        # Получаем embed для поиска соответствий
        role_mappings = {}
        if message.embeds:
            embed = message.embeds[0]
            # Парсим embed для поиска соответствий эмодзи-роль
            for field in embed.fields:
                if "рол" in field.name.lower() or "role" in field.name.lower():
                    lines = field.value.split('\n')
                    for line in lines:
                        if ' - ' in line:
                            emoji_part, role_part = line.split(' - ', 1)
                            emoji_str = emoji_part.strip()
                            role_match = re.search(r'<@&(\d+)>', role_part)
                            if role_match:
                                role_id = int(role_match.group(1))
                                role_mappings[emoji_str] = role_id

        # Восстанавливаем на основе реакций
        restored_count = 0
        role_reactions[message_id] = {}

        for reaction in message.reactions:
            emoji = reaction.emoji

            # Создаем ключ для поиска
            if isinstance(emoji, discord.Emoji):
                emoji_key = str(emoji.id)
                emoji_display = str(emoji)
            else:
                emoji_key = str(emoji)
                emoji_display = emoji

            # Ищем соответствующую роль
            role_id = None

            # Сначала ищем в распарсенном embed
            if emoji_display in role_mappings:
                role_id = role_mappings[emoji_display]
            else:
                # Пробуем найти по эмодзи в текстовом представлении
                for emoji_str, r_id in role_mappings.items():
                    if emoji_str == emoji_display:
                        role_id = r_id
                        break

            if role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    role_reactions[message_id][emoji_key] = role_id
                    restored_count += 1
                else:
                    await ctx.send(f"⚠️ Роль с ID {role_id} для эмодзи {emoji_display} не найдена!")
            else:
                await ctx.send(f"⚠️ Не найдено соответствие для эмодзи {emoji_display} в embed сообщения")

        if restored_count > 0:
            success_embed = discord.Embed(
                title="✅ Восстановление из реакций завершено!",
                description=f"Сообщение {message_id} восстановлено в системе ролей!\n\n**Восстановлено связей:** {restored_count}",
                color=0x00ff00
            )
            await ctx.send(embed=success_embed)
        else:
            await ctx.send("❌ Не удалось восстановить ни одной связи ролей!")

    except Exception as e:
        await ctx.send(f"❌ Ошибка при восстановлении из реакций: {e}")


@bot.command(name='force_restore',help='Принудительное восстановление с указанием соответствий эмодзи-роль (Укажите message_id и пары роль-эмодзи)')
@commands.has_permissions(administrator=True)
async def force_restore(ctx, message_id: int, *role_mappings):
    try:
        # Получаем сообщение по ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Сообщение с указанным ID не найдено в этом канале!")
            return

        # Парсим маппинги ролей
        mappings = {}
        for mapping in role_mappings:
            if '=' in mapping:
                emoji_str, role_mention = mapping.split('=', 1)
                emoji_str = emoji_str.strip()

                # Парсим роль из упоминания
                role_match = re.search(r'<@&(\d+)>', role_mention)
                if role_match:
                    role_id = int(role_match.group(1))
                    role = ctx.guild.get_role(role_id)
                    if role:
                        # Парсим эмодзи
                        emoji = parse_emoji(emoji_str, ctx.guild)
                        if emoji:
                            emoji_key = str(emoji.id) if isinstance(emoji, discord.Emoji) else str(emoji)
                            mappings[emoji_key] = role_id
                        else:
                            await ctx.send(f"⚠️ Не распознан эмодзи: {emoji_str}")
                    else:
                        await ctx.send(f"⚠️ Роль не найдена: {role_mention}")
                else:
                    await ctx.send(f"⚠️ Неверный формат упоминания роли: {role_mention}")

        if not mappings:
            await ctx.send("❌ Не указано валидных соответствий эмодзи-роль!")
            return

        # Восстанавливаем систему
        role_reactions[message_id] = mappings

        # Добавляем реакции если их нет
        for emoji_key, role_id in mappings.items():
            try:
                # Конвертируем emoji_key обратно в эмодзи объект
                if emoji_key.isdigit():
                    emoji = ctx.guild.get_emoji(int(emoji_key))
                else:
                    emoji = emoji_key

                if emoji:
                    reaction_exists = False
                    for reaction in message.reactions:
                        reaction_emoji = str(reaction.emoji.id) if hasattr(reaction.emoji, 'id') else str(
                            reaction.emoji)
                        if reaction_emoji == emoji_key:
                            reaction_exists = True
                            break

                    if not reaction_exists:
                        await add_reaction_to_message(message, emoji)
            except Exception as e:
                await ctx.send(f"⚠️ Ошибка при добавлении реакции {emoji_key}: {e}")

        success_embed = discord.Embed(
            title="✅ Принудительное восстановление завершено!",
            description=f"Сообщение {message_id} восстановлено в системе ролей!\n\n**Установлено связей:** {len(mappings)}",
            color=0x00ff00
        )
        await ctx.send(embed=success_embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка при принудительном восстановлении: {e}")


@bot.command(name='check_message',help='Проверяет сообщение и показывает информацию о нем (Укажите message_id)')
@commands.has_permissions(administrator=True)
async def check_message(ctx, message_id: int):
    try:
        # Получаем сообщение по ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Сообщение с указанным ID не найдено в этом канале!")
            return

        embed = discord.Embed(
            title="🔍 Информация о сообщении",
            description=f"ID: {message_id}",
            color=0x7289da
        )

        # Статус в системе ролей
        in_system = message_id in role_reactions
        embed.add_field(
            name="Статус в системе ролей",
            value="✅ В системе" if in_system else "❌ Не в системе",
            inline=False
        )

        # Информация о embed
        if message.embeds:
            embed_info = f"**Заголовок:** {message.embeds[0].title or 'Нет'}\n"
            embed_info += f"**Описание:** {message.embeds[0].description or 'Нет'}\n"
            embed_info += f"**Поля:** {len(message.embeds[0].fields)}"
            embed.add_field(name="Embed сообщения", value=embed_info, inline=False)
        else:
            embed.add_field(name="Embed сообщения", value="❌ Нет embed", inline=False)

        # Информация о реакциях
        if message.reactions:
            reactions_info = ""
            for reaction in message.reactions:
                emoji = reaction.emoji
                if isinstance(emoji, discord.Emoji):
                    reactions_info += f"{emoji} (`{emoji.id}`) - {reaction.count} реакции\n"
                else:
                    reactions_info += f"{emoji} - {reaction.count} реакции\n"
            embed.add_field(name="Реакции", value=reactions_info, inline=False)
        else:
            embed.add_field(name="Реакции", value="❌ Нет реакций", inline=False)

        # Если сообщение в системе, показываем связи
        if in_system:
            connections_info = ""
            for emoji_key, role_id in role_reactions[message_id].items():
                role = ctx.guild.get_role(role_id)
                if role:
                    # Пытаемся найти эмодзи для отображения
                    try:
                        emoji_id = int(emoji_key)
                        emoji_obj = ctx.guild.get_emoji(emoji_id)
                        if emoji_obj:
                            connections_info += f"{emoji_obj} → {role.mention}\n"
                        else:
                            connections_info += f"[Custom:{emoji_key}] → {role.mention}\n"
                    except ValueError:
                        connections_info += f"{emoji_key} → {role.mention}\n"

            embed.add_field(name="Связи в системе", value=connections_info or "Нет связей", inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка при проверке сообщения: {e}")

bot.run(TOKEN)