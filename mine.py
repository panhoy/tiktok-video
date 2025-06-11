import os
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import asyncio


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


BOT_TOKEN = "7864369579:AAHJUdTOp-2FngRggPaqmBSg5FIudHE_f3M"

class VideoDownloader:
    def __init__(self):
        self.download_path = "downloads/"
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
    
    def download_video(self, url, max_size_mb=50):
        """Download video using yt-dlp"""
        try:
            ydl_opts = {
                'outtmpl': f'{self.download_path}%(title)s.%(ext)s',
                'format': 'best[filesize<?50M]/best',  # Limit file size
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                

                if duration > 600:
                    return None, "Video too long (max 10 minutes)"
                
                ydl.download([url])
                

                for file in os.listdir(self.download_path):
                    if title.replace('/', '_') in file or file.startswith(title[:20]):
                        return os.path.join(self.download_path, file), None
                        
                return None, "Download failed"
                
        except Exception as e:
            return None, f"Error: {str(e)}"

downloader = VideoDownloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_message = """
🎬 *Video Downloader Bot*

Send me a video URL and I'll download it for you!

*Supported platforms:*
• YouTube
• Instagram
• TikTok
• Twitter/X
• Facebook
• And many more!

*Commands:*
/start - Show this message
/help - Get help

*Usage:*
Just send me a video URL and I'll process it!

*Limits:*
• Max file size: 50MB
• Max duration: 10 minutes
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
🆘 *How to use this bot:*

1. Find a video you want to download
2. Copy the video URL
3. Send the URL to this bot
4. Wait for the bot to process and send your video

*Supported URLs:*
• https://youtube.com/watch?v=...
• https://youtu.be/...
• https://instagram.com/p/...
• https://tiktok.com/@user/video/...
• https://twitter.com/user/status/...
• And many more platforms!

*Note:* Large videos may take some time to process.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def download_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video download requests"""
    url = update.message.text.strip()
    

    if not (url.startswith('http://') or url.startswith('https://')):
        await update.message.reply_text("❌ Please send a valid URL starting with http:// or https://")
        return
    

    processing_msg = await update.message.reply_text("⏳ Processing your request... Please wait.")
    
    try:

        loop = asyncio.get_event_loop()
        file_path, error = await loop.run_in_executor(None, downloader.download_video, url)
        
        if error:
            await processing_msg.edit_text(f"❌ {error}")
            return
            
        if not file_path or not os.path.exists(file_path):
            await processing_msg.edit_text("❌ Failed to download video. Please check the URL and try again.")
            return
        

        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        
        if file_size > 50:
            await processing_msg.edit_text("❌ Video file is too large (>50MB). Please try a shorter video.")
            os.remove(file_path)  # Clean up
            return
        
        await processing_msg.edit_text("📤 Uploading video...") 
        

        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ Here's your downloaded video!",
                supports_streaming=True
            )
        

        os.remove(file_path)
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ An error occurred: {str(e)}")
        logger.error(f"Error in download_video_handler: {e}")

async def handle_non_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-URL messages"""
    await update.message.reply_text(
        "🔗 Please send me a video URL to download.\n\n"
        "Use /help to see supported platforms and usage instructions."
    )

def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # URL handler (messages containing http/https)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'https?://'), 
        download_video_handler
    ))
    
    # Non-URL message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'https?://'),
        handle_non_url_message
    ))
    
    # Start the bot
    print("🤖 Bot is starting...")
    print("Press Ctrl+C to stop the bot")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()