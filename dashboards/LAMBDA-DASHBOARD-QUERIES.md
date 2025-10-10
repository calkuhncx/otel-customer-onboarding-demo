# Lambda Dashboard Queries - Manual Setup Guide

## Dashboard Configuration
- **Name:** cal-onboarding-lambda-arm64 Observability
- **Time Frame:** Last 1 hour (3600s)
- **Function Filter:** `FunctionName="cal-onboarding-lambda-arm64"`

---

## Widget 1: Total Invocations (Gauge)
**Type:** Gauge  
**Title:** Total Invocations  
**Description:** Total number of Lambda invocations in selected time period

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_Invocations_sum{FunctionName="cal-onboarding-lambda-arm64"}[${__range}]))
```

**Settings:**
- Unit: Number
- Min: 0
- Max: 100 (or auto)
- Show Inner Arc: No
- Show Outer Arc: No
- Color: Blue/Info

---

## Widget 2: Invocations Over Time (Line Chart)
**Type:** Line Chart  
**Title:** Invocations Over Time  
**Description:** Number of Lambda invocations per minute

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_Invocations_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Number
- Legend: Show (with SUM, MAX columns)
- Stacked: No
- Connect Nulls: No

---

## Widget 3: Error Rate % (Gauge)
**Type:** Gauge  
**Title:** Error Rate (%)  
**Description:** Percentage of invocations that resulted in errors

**Query:**
```promql
100 * sum(sum_over_time(amazonaws_com_AWS_Lambda_Errors_sum{FunctionName="cal-onboarding-lambda-arm64"}[${__range}])) / sum(sum_over_time(amazonaws_com_AWS_Lambda_Invocations_sum{FunctionName="cal-onboarding-lambda-arm64"}[${__range}]))
```

**Settings:**
- Unit: Percent
- Min: 0
- Max: 100
- Show Inner Arc: Yes
- Show Outer Arc: Yes
- Thresholds:
  - 0-5%: Green
  - 5-10%: Yellow/Warning
  - 10-100%: Red/Error

---

## Widget 4: Errors Over Time (Line Chart)
**Type:** Line Chart  
**Title:** Errors Over Time  
**Description:** Number of Lambda errors per minute

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_Errors_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Number
- Legend: Show (with SUM, MAX columns)
- Color Scheme: Red/Severity
- Stacked: Yes (Absolute)

---

## Widget 5: Average Duration (Line Chart)
**Type:** Line Chart  
**Title:** Avg Duration  
**Description:** Average Lambda execution duration in milliseconds

**Query:**
```promql
(sum_over_time(amazonaws_com_AWS_Lambda_Duration_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m]) / sum_over_time(amazonaws_com_AWS_Lambda_Duration_count{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Milliseconds
- Legend: Show (with AVG column)
- Tooltip: Show labels, Single

---

## Widget 6: Max Duration (Line Chart)
**Type:** Line Chart  
**Title:** Max Duration  
**Description:** Maximum Lambda execution duration

**Query:**
```promql
max(max_over_time(amazonaws_com_AWS_Lambda_Duration_max{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Milliseconds
- Legend: Show (with MAX column)
- Color Scheme: Red/Severity

---

## Widget 7: Min Duration (Line Chart)
**Type:** Line Chart  
**Title:** Min Duration  
**Description:** Minimum Lambda execution duration

**Query:**
```promql
min(min_over_time(amazonaws_com_AWS_Lambda_Duration_min{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Milliseconds
- Legend: Show (with MIN column)

---

## Widget 8: Concurrent Executions (Line Chart)
**Type:** Line Chart  
**Title:** Concurrent Executions  
**Description:** Number of concurrent Lambda executions

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_ConcurrentExecutions_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Number
- Legend: Show (with SUM column)
- Stacked: No

---

## Widget 9: Throttles (Line Chart)
**Type:** Line Chart  
**Title:** Throttles  
**Description:** Number of throttled invocations (capacity issues)

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_Throttles_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Number
- Legend: Show (with SUM, MAX columns)
- Color Scheme: Red/Severity
- Alert Threshold: > 0 (any throttling is bad)

---

## Widget 10: Async Event Age (Line Chart)
**Type:** Line Chart  
**Title:** Async Event Age  
**Description:** Time between Lambda queuing event and invocation

**Query:**
```promql
(sum(sum_over_time(amazonaws_com_AWS_Lambda_AsyncEventAge_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) / sum(sum_over_time(amazonaws_com_AWS_Lambda_AsyncEventAge_count{FunctionName="cal-onboarding-lambda-arm64"}[1m]))) or on() vector(0)
```

**Settings:**
- Unit: Milliseconds
- Legend: Show (with MIN, MAX, AVG columns)

---

## Widget 11: Async Events Received (Line Chart)
**Type:** Line Chart  
**Title:** Async Events Received  
**Description:** Asynchronous invocations from event sources

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_AsyncEventsReceived_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Number
- Legend: Show (with SUM column)

---

## Widget 12: Async Events Dropped (Line Chart)
**Type:** Line Chart  
**Title:** Async Events Dropped  
**Description:** Events dropped without executing (serious issue!)

**Query:**
```promql
sum(sum_over_time(amazonaws_com_AWS_Lambda_AsyncEventsDropped_sum{FunctionName="cal-onboarding-lambda-arm64"}[1m])) or on() vector(0)
```

**Settings:**
- Unit: Number
- Legend: Show (with SUM column)
- Color Scheme: Red/Severity
- Alert Threshold: > 0 (any dropped events is critical)

---

## OPTIONAL: SQS Integration Widgets

### Widget 13: SQS Queue Depth (Line Chart)
**Type:** Line Chart  
**Title:** SQS Queue Age  
**Description:** How long messages wait in queue before Lambda processes them

**Query:**
```promql
max(amazonaws_com_AWS_SQS_ApproximateAgeOfOldestMessage{QueueName=~".*cal-onboarding-queue.*"}) or on() vector(0)
```

**Settings:**
- Unit: Seconds
- Legend: Show (with MAX column)
- Alert Thresholds:
  - Warning: > 60s
  - Critical: > 300s

---

### Widget 14: SQS Messages Sent (Line Chart)
**Type:** Line Chart  
**Title:** SQS Messages Sent  
**Description:** Messages sent to queue (from ECS)

**Query:**
```promql
sum(rate(amazonaws_com_AWS_SQS_NumberOfMessagesSent{QueueName=~".*cal-onboarding-queue.*"}[1m])) * 60 or on() vector(0)
```

**Settings:**
- Unit: Messages/minute
- Legend: Show

---

### Widget 15: SQS Messages Processed (Line Chart)
**Type:** Line Chart  
**Title:** SQS Messages Processed  
**Description:** Messages processed by Lambda (deleted from queue)

**Query:**
```promql
sum(rate(amazonaws_com_AWS_SQS_NumberOfMessagesDeleted{QueueName=~".*cal-onboarding-queue.*"}[1m])) * 60 or on() vector(0)
```

**Settings:**
- Unit: Messages/minute
- Legend: Show

---

## OPTIONAL: Application Metrics

### Widget 16: End-to-End Success Rate (Gauge)
**Type:** Gauge  
**Title:** E2E Success Rate  
**Description:** Overall system success rate from ECS API

**Query:**
```promql
(sum(rate(onboarding_api_success_total_total[5m])) / sum(rate(onboarding_api_requests_total_total[5m]))) * 100
```

**Settings:**
- Unit: Percent
- Min: 0
- Max: 100
- Thresholds:
  - 95-100%: Green
  - 90-95%: Yellow
  - 0-90%: Red

---

## Dashboard Layout Recommendations

### Row 1: Overview (Height: 19)
- Widget 1: Total Invocations (Gauge)
- Widget 2: Invocations Over Time (Line Chart)

### Row 2: Errors (Height: 19)
- Widget 3: Error Rate % (Gauge)
- Widget 4: Errors Over Time (Line Chart)

### Row 3: Performance (Height: 25)
- Widget 5: Avg Duration (Line Chart)

### Row 4: Performance Detail (Height: 15)
- Widget 6: Max Duration (Line Chart)
- Widget 7: Min Duration (Line Chart)

### Row 5: Concurrency & Throttling (Height: 17)
- Widget 8: Concurrent Executions (Line Chart)
- Widget 9: Throttles (Line Chart)

### Row 6: Async Events (Height: 15)
- Widget 11: Async Events Received (Line Chart)
- Widget 12: Async Events Dropped (Line Chart)

### Row 7: Async Event Age (Height: 14)
- Widget 10: Async Event Age (Line Chart)

### Row 8 (Optional): SQS Integration (Height: 19)
- Widget 13: SQS Queue Age (Line Chart)
- Widget 14: SQS Messages Sent vs Processed (Line Chart - 2 queries)

### Row 9 (Optional): E2E Metrics (Height: 19)
- Widget 16: E2E Success Rate (Gauge)

---

## Important Notes

1. **Time Range Variable:** `${__range}` is used in gauge queries for total aggregations
2. **Null Handling:** All queries end with `or on() vector(0)` to prevent empty graphs
3. **Window Functions:** Most line charts use `[1m]` (1 minute) windows
4. **Aggregations:** Use `sum_over_time()` for totals, `rate()` for per-second rates
5. **Hard-Coded Filter:** All queries include `FunctionName="cal-onboarding-lambda-arm64"`

---

## Quick Copy-Paste Queries (Without Filters)

If you want to make it work for ALL Lambda functions, replace:
```promql
{FunctionName="cal-onboarding-lambda-arm64"}
```

With variables:
```promql
{FunctionName=~"{{FunctionName}}"}
```

Then add a dashboard variable:
- Name: FunctionName
- Type: Label Value
- Metric: amazonaws_com_AWS_Lambda_Invocations
- Label: FunctionName

---

## Alerting Recommendations

Configure alerts for:
1. **Error Rate > 5%** (Warning) or > 10% (Critical)
2. **Any Throttles** (Warning)
3. **Any Dropped Async Events** (Critical)
4. **SQS Queue Age > 5 minutes** (Critical)
5. **Duration > 2x normal** (Warning)

---

## Next Steps

1. Open Coralogix → Dashboards → Create New Dashboard
2. Name it: "cal-onboarding-lambda-arm64 Observability"
3. Add widgets one by one using the queries above
4. Arrange in rows as recommended
5. Save and set time range to "Last 1 hour"

