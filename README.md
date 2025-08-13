# English Words Memorizer

A modern Flask web application for memorizing English vocabulary words with intelligent spaced repetition using the FSRS algorithm, embedded dictionary, CSV import/export functionality, and Anki export support.

## ✨ Features

- **🧠 FSRS Algorithm**: Free Spaced Repetition Scheduler for optimal learning intervals
- **📚 Embedded Dictionary**: Built-in English dictionary with automatic definition lookup
- **📊 Smart Study Planning**: Configurable daily study goals with intelligent scheduling
- **🔄 CSV Import/Export**: Bulk import words (even just word lists!) and export progress
- **📱 Anki Export**: Export your words to Anki for mobile study
- **📈 Progress Tracking**: Comprehensive statistics and learning analytics
- **🎯 Interactive Study Mode**: Flashcard-style learning with quality rating system
- **🎨 Modern UI**: Beautiful, responsive interface built with Bootstrap 5
- **🔍 Word Management**: Add, edit, delete, and organize vocabulary
- **📅 Review Scheduling**: Automatic scheduling based on your performance

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### 2. Open your browser
Navigate to `http://localhost:5000`

### 3. Import your first words
- Go to "Import CSV" 
- Upload a simple CSV with just a "word" column
- The app will automatically look up definitions!

## 📁 CSV Import Options

### Option 1: Simple Word List (Recommended)
Just provide a list of words - our embedded dictionary handles the rest!

```csv
word
serendipity
ubiquitous
ephemeral
mellifluous
```

### Option 2: Full Word Data
Provide complete information for each word:

```csv
word,meaning,example_sentence,part_of_speech,difficulty_level
serendipity,pleasant surprise,Meeting you here was pure serendipity!,noun,medium
ubiquitous,everywhere,Smartphones are ubiquitous in modern society,adjective,hard
```

## 🧠 FSRS Algorithm

The Free Spaced Repetition Scheduler (FSRS) optimizes your learning schedule based on:

- **Retention Rate**: How well you remember each word
- **Difficulty**: How hard each word is for you  
- **Optimal Intervals**: When to review for maximum retention

### Quality Rating Scale
- **0** - Complete blackout
- **1** - Incorrect response  
- **2** - Hard to recall
- **3** - Correct with difficulty
- **4** - Correct with hesitation
- **5** - Perfect response

## 📊 Study Planning

Configure your daily study goals:
- **Beginner**: 10-15 words/day
- **Intermediate**: 20-30 words/day  
- **Advanced**: 30-50 words/day

The FSRS algorithm automatically schedules reviews based on your performance.

## 🔧 Project Structure

```
project/
├── app.py                      # Main Flask application with FSRS
├── stardict.db                # Embedded dictionary database
├── requirements.txt            # Python dependencies
├── README.md                  # This file
├── templates/                 # HTML templates
│   ├── base.html             # Base template with navigation
│   ├── index.html            # Home page with study plan
│   ├── words.html            # Words list with FSRS status
│   ├── add_word.html         # Add word form
│   ├── edit_word.html        # Edit word form
│   ├── import_csv.html       # CSV import with dictionary info
│   ├── study.html            # Study mode with quality rating
│   ├── study_plan.html       # Study plan configuration
│   └── progress.html         # Progress tracking & analytics
├── static/                    # Static files
│   ├── css/style.css         # Custom CSS styles
│   └── js/app.js             # JavaScript functionality
├── scripts/                   # Utility scripts
│   ├── convert_wordlist_to_csv.py    # Convert word lists to CSV
│   └── enhance_csv.py                # Enhance CSV with metadata
└── words.db                   # SQLite database (created automatically)
```

## 🗄️ Database Schema

### Words Table
```sql
CREATE TABLE word (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word VARCHAR(100) UNIQUE NOT NULL,
    meaning TEXT NOT NULL,
    example_sentence TEXT,
    part_of_speech VARCHAR(50),
    difficulty_level VARCHAR(20) DEFAULT 'medium',
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    times_studied INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    last_studied DATETIME,
    next_review DATETIME,           -- FSRS scheduling
    ease_factor FLOAT DEFAULT 2.5,  -- FSRS ease factor
    interval INTEGER DEFAULT 0,      -- FSRS interval
    repetitions INTEGER DEFAULT 0    -- FSRS repetitions
);
```

### Study Plan Table
```sql
CREATE TABLE study_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    words_per_day INTEGER DEFAULT 20,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Study Sessions Table
```sql
CREATE TABLE study_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL,
    quality INTEGER NOT NULL,        -- 0-5 quality rating
    review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    next_review DATETIME,
    ease_factor FLOAT,
    interval INTEGER
);
```

## 📚 Embedded Dictionary

The application includes a built-in English dictionary (`stardict.db`) that provides:
- **Definitions**: Clear, accurate meanings
- **Parts of Speech**: Grammatical classification  
- **Example Sentences**: Usage in context
- **Phonetic Spellings**: Pronunciation guides

Words not in the dictionary can still be imported and defined manually.

## 🎯 Study Workflow

1. **Import Words**: Upload CSV or add manually
2. **Set Study Plan**: Configure daily word goals
3. **Study Daily**: Use quality rating system (0-5)
4. **Track Progress**: Monitor learning analytics
5. **Export**: Share with Anki or other tools

## 📱 Export Options

### CSV Export
Full word data with FSRS information for backup/analysis.

### Anki Export  
Anki-compatible format for mobile study:
- Front: Word
- Back: Meaning + Example + Part of Speech

## 🛠️ Configuration

Key settings in `app.py`:
- `SECRET_KEY`: Change for production
- `SQLALCHEMY_DATABASE_URI`: Database connection
- `FSRS_WEIGHTS`: Algorithm parameters (advanced)

## 📦 Dependencies

- **Flask 3.0.0**: Web framework
- **Flask-SQLAlchemy 3.1.1**: Database ORM
- **Pandas 2.2.3+**: CSV processing
- **Python-dotenv 1.0.0**: Environment management
- **Werkzeug 3.0.1**: WSGI utilities

## 🌐 Browser Support

- Chrome/Chromium (recommended)
- Firefox
- Safari  
- Edge

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

If you encounter issues:

1. Check the documentation above
2. Review error messages in the application
3. Check browser console for JavaScript errors
4. Open an issue in the repository

## 🚀 Future Enhancements

- **Advanced FSRS**: Customizable algorithm parameters
- **Multiple Languages**: Support for other languages
- **Audio Pronunciation**: Text-to-speech integration
- **Mobile App**: Native mobile application
- **Cloud Sync**: Cross-device synchronization
- **Advanced Analytics**: Detailed learning insights
- **Social Features**: Word sharing and competitions
- **API Integration**: External dictionary services

## 🎓 Learning Resources

- [FSRS Algorithm Documentation](https://github.com/ishiko732/FSRS4Anki)
- [Spaced Repetition Theory](https://en.wikipedia.org/wiki/Spaced_repetition)
- [Vocabulary Learning Strategies](https://www.vocabulary.com/)

---

**Happy Learning! 🎉**

Built with ❤️ using Flask and the FSRS algorithm for optimal vocabulary retention.


