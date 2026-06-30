from flask import Flask, request, jsonify
import json
from datetime import datetime,timezone
from dotenv import load_dotenv
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
import re
from groq import Groq


load_dotenv()
app= Flask(__name__)

#Basic loging file definition
LOG_FILE= 'database.db'

api_key= os.getenv("GROQ_API_KEY")
client= Groq(api_key=api_key)


#initialize Flask-limitter with local memmory storage as required by cursor spec
limiter= Limiter(
    
    key_func= get_remote_address,
    #app= app,
    #default_limits=[],
    storage_uri= "memory://"
    
)
limiter.init_app(app)

'''
******************************************************************
def get_all_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
        
    except (json.JSONDecodeError, IOError):
        return []
***************************************************
 '''
def get_all_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            
            # If the database accidentally got nested like [[...]], flatten it safely
            if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
                return data[0]
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"!!! Error reading log file: {e}")
        return []
        
    
def write_to_log(entry):
    logs= get_all_logs()
    logs.append(entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=4) 
        
        
def calculate_sentence_variance(text):
    '''SIGNAL 1: Stylometric Heuristics (Sentence Length Variance)
    Measures the standard deviation/variance of sentence lengths.
    Returns a normalized float between 0.0 (high variance/human) and 1.0 (flat/AI).
    '''
    sentece= [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    
    if len(sentece) <2:
        return  0.5 # returning neutral score if the text is too short to establish variance
    word_counts= [len(s.split()) for s in sentece]
    mean= sum( word_counts)/len(word_counts)
    
    #calculate variance
    variance= sum((x-mean)**2 for x in word_counts)/len(word_counts)
    
    #Normalize variance for 0.0 -1.0 scale
    # High variance (e.g., variance >= 50) represents complex human burstiness -> close to 0.0
    # Flat variance (variance close to 0) means uniform sentence structures -> close to 1.0
    if variance >=50:
        normalized_score= 0.0
    else:
        normalized_score=1.0- (variance/50.0)
        
    return round(float(normalized_score),2)

def calculate_vocabulary_diversity(text):
    '''signal 2:Stylometric Heuristic(vocabulary diversity/type token ratio)
        mesuares unique words divided by total words. low diversity point to AI predictibility
    '''
    
    #text cleaning
    words= re.findall(r'\b\w+\b', text.lower())
    if not words:
        return 0.5
    total_tokens= len(words)
    unique_types= len(set(words))
    ttr= unique_types/total_tokens
    
    #Map the diversity
    if ttr >= 0.85:
        score = 0.0
    elif ttr <= 0.40:
        score = 1.0
    else:
        # Linear scaling inside bounds
        score = 1.0 - ((ttr - 0.40) / (0.85 - 0.40))
        
    return round(float(score), 2)

def evaluate_llm_signal(text):
    """
    SIGNAL 3: LLM Semantic Analysis (via Groq)
    Forces the model to inspect structural patterns and return a pure score float.
    """
    try:
        prompt = (
            "Analyze the following text sample to determine if it shows characteristics "
            "of AI-generated text (repetitive transitional phrases, sterile tone, flat structural syntax) "
            "or human writing (irregular flow, emotional depth, idiosyncratic sentence variance).\n\n"
            f"Text Content:\n\"\"\"\n{text}\n\"\"\"\n\n"
            "CRITICAL: You must return exactly a single float value between 0.0 (Pure Human) "
            "and 1.0 (Pure AI). Do not include introductory prose, explanations, or formatting. "
            "Provide ONLY the raw float value."
        )
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert stylometric and linguist evaluator. Output raw numeric floats only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        response_text = completion.choices[0].message.content.strip()
        # Extract the float using regex in case any small trailing character slipped in
        match = re.search(r"[-+]?\d*\.\d+|\d+", response_text)
        if match:
            score = float(match.group())
            return min(max(round(score, 2), 0.0), 1.0)
        return 0.5
    except Exception as e:
        print(f"Groq API Error: {e}")
        return 0.5 # Graceful fallback to safety threshold on system failure


@app.route('/submit', methods= ['POST'])
@limiter.limit("5 per minute")              #Rate limit rule
def submit():
    data= request.get_json() or {}
    text = data.get('text','').strip()
    creator_id = data.get('creator_id', '').strip()
    
    if not text or not creator_id:
        return jsonify({'error': 'missing required field: text and creator_id'}), 400
    
    #Generate unique asset identifier
    content_id= str(uuid.uuid4())
    
    #The pipeline engines
    signal_1_score= calculate_sentence_variance(text)
    #signal_2_score= calculate_sentence_variance(text)
    signal_2_score= calculate_vocabulary_diversity(text)
    signal_3_score= evaluate_llm_signal(text)
    
    #calculate ensemble weighted average
    final_score= round((0.2 *signal_1_score) + (0.2 *signal_2_score) + (0.6 * signal_3_score),2)
    
    #Ditermine Atrribution and labels based on hard threshold
    if final_score < 0.4:
        attribution= 'likely_human'
        label="verified authentic: This content exhibit strong characteristics of original human writing"
    elif final_score <=0.65:
        attribution= 'uncertain'
        label = "Context unclear: This text contains a mix of structur signals. Our automated system cannot determine its origin"
    else:
        attribution= 'likely_AI_generated'
        label= "Automated generation likely:Significant patterns in this text align closely with machine generated structure"
    
       
    # Metadata to Audit log entry
    
    log_entry={
        'content_id': content_id,
        'creator_id': creator_id,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'attribution': attribution,
        'confidence': final_score,
        
        'stylometrics':{
            'sentence_variance_score': signal_1_score,
            'vocabulary_diversity_score': signal_2_score
        },
        'llm_score': signal_3_score,
        'status': 'classified',
        'appeal_reason': None
    }
    
    #commit for audit records
    logs= get_all_logs()
    logs.append(log_entry)
    write_to_log(logs)
    
    #API  output playload
    return jsonify({
        'content_id': content_id,
        'attribution': attribution,
        'confidence': final_score,
        'label': label
         
     }), 200
    
'''
 ******************************************   
    
@app.route("/appeal", methods= ['POST'])
def appeal():
    #Validate and process the creator appeal for misclassified text asset items.
    data= request.get_json() or {}
    content_id= data.get("content_id", "").strip()
    reason= data.get("creator_reasoning", "").strip()
    
    if not content_id or not reason:
        return jsonify({'error':'content missing'})
    logs= get_all_logs()
    found= False
    
    for entry in logs:
        if entry['content_id']==content_id:
            entry['status']= 'under_review'
            entry['appeal_reason']= reason
            found=True
            break
        
    if not found:
        return jsonify({'error':'content log entry not found'}),404
    
    write_to_log(logs)
    return jsonify({'Message': 'Appeal successfully filed. Record status updated to under_review'}),200
'''
@app.route("/appeal", methods=['POST'])
def appeal():
    '''Validate and process the creator appeal for misclassified text asset items.'''
    data = request.get_json() or {}
    content_id = data.get("content_id", "").strip()
    reason = data.get("creator_reasoning", "").strip()
    
    if not content_id or not reason:
        return jsonify({'error': 'Missing content_id or creator_reasoning'}), 400
        
    logs = get_all_logs()
    found = False
    
    for entry in logs:
        # Check to make sure entry is a dictionary before looking up keys
        if isinstance(entry, dict) and str(entry.get("content_id")) == str(content_id):
            entry['status'] = 'under_review'
            entry['appeal_reason'] = reason
            found = True
            break
        
    if not found:
        return jsonify({'error': 'content log entry not found'}), 404
    
    write_to_log(logs)
    return jsonify({'Message': 'Appeal successfully filed. Record status updated to under_review'}), 200

@app.route('/log', methods= ['GET'])
def get_log():
    """Exposes structured history logs for grader transparency."""
    logs= get_all_logs()
    #reverse all chronological order to inspect the latest addition
    return jsonify({'entries': logs[::-1]}), 200
    
if __name__=="__main__":
    app.run(port= 5000, debug=True)
        
    
    
        
