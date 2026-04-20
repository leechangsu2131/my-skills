import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { image, type, questionCount } = await req.json();
    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY is not configured");

    let systemPrompt = "";
    let userPrompt = "";

    if (type === "answer-key") {
      systemPrompt = `You are an exam answer key extractor. Extract all answers from the provided exam answer sheet image.
Return a valid JSON object with this exact structure:
{"answerKeys": [{"questionNumber": 1, "answer": "답", "type": "objective", "points": 1}, ...]}

Rules:
- questionNumber starts from 1
- type is "objective" for multiple choice (객관식) or "subjective" for short answer (주관식)
- For objective questions, answer should be the number (1,2,3,4,5) or letter
- For subjective questions, answer should be the exact text
- Default points to 1 if not specified in the image
- Extract ALL questions visible in the image`;
      userPrompt = "Extract the answer key from this exam document. Return JSON only.";
    } else {
      systemPrompt = `You are a student exam answer extractor. Extract the student's answers from the provided exam paper image.
Return a valid JSON object with this exact structure:
{"studentName": "학생이름 or empty string if not found", "answers": [{"questionNumber": 1, "answer": "학생답안", "type": "objective"}, ...]}

Rules:
- Extract the student name if visible (look for 이름, 성명, Name fields)
- questionNumber starts from 1
- type is "objective" for multiple choice or "subjective" for short answer
- For objective questions, extract the selected number/letter
- For unanswered questions, set answer to empty string ""
- Extract ALL answers visible, expecting approximately ${questionCount || 'unknown number of'} questions
- Be precise with the answers - extract exactly what the student wrote/marked`;
      userPrompt = `Extract the student's answers from this exam paper. There should be approximately ${questionCount || 'several'} questions. Return JSON only.`;
    }

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-2.5-flash",
        messages: [
          { role: "system", content: systemPrompt },
          {
            role: "user",
            content: [
              { type: "text", text: userPrompt },
              { type: "image_url", image_url: { url: `data:application/pdf;base64,${image}` } },
            ],
          },
        ],
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error("AI gateway error:", response.status, errText);

      if (response.status === 429) {
        return new Response(JSON.stringify({ error: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요." }), {
          status: 429,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      if (response.status === 402) {
        return new Response(JSON.stringify({ error: "크레딧이 부족합니다." }), {
          status: 402,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      throw new Error(`AI gateway error: ${response.status}`);
    }

    const aiResult = await response.json();
    const content = aiResult.choices?.[0]?.message?.content || "";

    // Parse JSON from response (handle markdown code blocks)
    let parsed;
    try {
      const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
      const jsonStr = jsonMatch ? jsonMatch[1] : content;
      parsed = JSON.parse(jsonStr.trim());
    } catch {
      console.error("Failed to parse AI response:", content);
      throw new Error("AI 응답을 파싱할 수 없습니다.");
    }

    return new Response(JSON.stringify(parsed), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("ocr-extract error:", e);
    return new Response(
      JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
