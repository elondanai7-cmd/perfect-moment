# פריסה לאתר חי (Hugging Face Spaces, חינם)

זה בונה אתר אמיתי: מבקר מעלה סרטון → הפייפליין רץ אוטומטית בשרת → התמונות
הכי טובות חוזרות אליו על המסך. בלי וואטסאפ, בלי שלב ידני. עלות: **$0**.

דורש חשבון חינמי ב-huggingface.co (אם אין לך עדיין — הירשם שם קודם).

## שלבים (פעם אחת, ~10 דקות)

1. **התחברות** (בטרמינל, בתיקיית הפרויקט):
   ```
   hf auth login
   ```
   יבקש טוקן — צור אחד ב־huggingface.co/settings/tokens עם הרשאת "Write".

2. **בניית תיקיית ה-Space** (עותק נקי, בלי טסטים/וידאו/git history):
   ```
   mkdir -p ../perfect-moment-space/perfectmoment
   cp -r perfectmoment/*.py ../perfect-moment-space/perfectmoment/
   cp webapp/app.py ../perfect-moment-space/app.py
   cp webapp/requirements.txt ../perfect-moment-space/requirements.txt
   ```
   ואז ערוך ב-`../perfect-moment-space/app.py` את השורה
   `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`
   ל-`sys.path.insert(0, str(Path(__file__).resolve().parent))`
   (כי עכשיו `perfectmoment/` יושב ליד `app.py`, לא תיקייה מעליו).

3. **צור את ה-Space** (שם לבחירה, למשל `perfect-moment`):
   ```
   hf repo create perfect-moment --type space --space_sdk gradio
   ```

4. **הוסף את קובץ ה-README עם ה-card** — צור
   `../perfect-moment-space/README.md`:
   ```
   ---
   title: הרגע המושלם
   emoji: 📸
   sdk: gradio
   sdk_version: 5.9.1
   app_file: app.py
   pinned: false
   ---
   ```

5. **פוש**:
   ```
   cd ../perfect-moment-space
   git init
   git remote add origin https://huggingface.co/spaces/<היוזר-שלך>/perfect-moment
   git add .
   git commit -m "initial deploy"
   git push -u origin main
   ```

6. תוך כמה דקות ה-Space יבנה את עצמו (רואים לוג בנייה באתר). כשמוכן —
   הכתובת `https://huggingface.co/spaces/<היוזר-שלך>/perfect-moment` היא
   האתר החי שלך. אפשר לשים אותה כ-iframe או קישור מתוך `landing/index.html`.

## מה זה בפועל, בלי באזז

- "סוכן 1" = הדף עצמו (Gradio) — מקבל את הווידאו.
- "סוכן 2" = `perfectmoment.pipeline.run()` — אותו קוד בדיוק שכבר עבר 32
  טסטים, לא LLM, לא API בתשלום. הוא זה שבודק חדות/עיניים/חיוך/קומפוזיציה
  ומחזיר את התמונות הכי טובות.
- שלב ה-QA הוויזואלי הידני של `dispatcher/` (שבו Claude מסתכל בעצמו על
  התמונות) **לא** רץ כאן אוטומטית — כי זה בפועל שלב שדורש AI vision בתשלום
  כדי לרוץ בלי בן אדם. אם בעתיד תרצה להוסיף שכבת בדיקה נוספת אוטומטית,
  זו תהיה קריאת API בתשלום — לא משהו שאפשר לעשות ב-$0.
