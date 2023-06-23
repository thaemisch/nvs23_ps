from wordcloud import WordCloud
import matplotlib.pyplot as plt
import subprocess

# Get all GitHub commit messages via command line
# git log --pretty=format:%s > commitMessages.txt
#subprocess.call(['git', 'log', '--pretty=format:%s', '>', 'commitmsgs.txt'])
with open('commitmsgs.txt', 'r') as f:
    textParts = f.read().split('\n')

for textPart in textParts:
    if "merge" in textPart.lower():
        textParts.remove(textPart)
    if "wordcloud" or "worldcloud" in textPart.lower():
        textParts.remove(textPart)

text = ' '.join(textParts)

# Create a WordCloud object
wordcloud = WordCloud(width=800, height=800, background_color='white', min_font_size=10).generate(text)

# Display the generated image:
plt.figure(figsize=(8,8), facecolor=None)
plt.imshow(wordcloud)
plt.axis("off")
plt.tight_layout(pad=0)

plt.savefig('wordcloud.png')